from flask import Flask, request, jsonify
import subprocess
import re
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

serpapi_key = os.getenv('SERPAPI_KEY')

# In-memory storage for conversation history
memory = {}

class OllamaLocalModel:
    def __init__(self, model="llama3.2"):
        self.model = model
        # Verify model availability at initialization
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            if self.model not in result.stdout:
                raise ValueError(f"Model {self.model} not found in Ollama. Available models:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Ollama service is not available: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Ollama model: {str(e)}")

    def invoke(self, prompt):
        if not prompt or not isinstance(prompt, str):
            return "Error: Invalid prompt"
            
        try:
            result = subprocess.run(
                ["ollama", "run", self.model, prompt],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                print(f"Ollama error: {error_msg}")  # Log error for debugging
                return f"Error: Model execution failed - {error_msg}"
                
            response = result.stdout.strip()
            if not response:
                return "Error: Empty response from model"
                
            return response
            
        except subprocess.TimeoutExpired:
            print(f"Request timeout for prompt: {prompt[:100]}...")  # Log timeout
            return "Error: Request timed out after 120 seconds"
        except subprocess.CalledProcessError as e:
            print(f"Process error: {str(e)}")  # Log process error
            return f"Error: {str(e)}"
        except Exception as e:
            print(f"Unexpected error: {str(e)}")  # Log unexpected errors
            return f"Unexpected error: {str(e)}"

# Initialize the LLM using Ollama's gemma2:9b model
llm = OllamaLocalModel(model="llama3.2")

# Add a message to memory
def add_to_memory(session_id, role, message):
    if not message or not isinstance(message, str):
        print(f"Invalid message for session {session_id}: {type(message)}")
        return
        
    message = message.strip()
    if not message:
        return
        
    if session_id not in memory:
        memory[session_id] = []
    
    # Ensure memory doesn't grow too large
    if len(memory) > 1000:  # Limit total sessions
        oldest_session = min(memory.keys())
        del memory[oldest_session]
    
    memory[session_id].append({"role": role, "message": message})
    # Keep only the last two exchanges
    if len(memory[session_id]) > 4:
        memory[session_id] = memory[session_id][-4:]

# Retrieve the last two exchanges for context
def get_recent_memory(session_id):
    return memory.get(session_id, [])

# Improved function to extract only the assistant's final response
def extract_assistant_response(full_response):
    match = re.search(r'Assistant:\s*(.*)', full_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return full_response.strip()

# Function to handle Serp API call
def call_serp_api(query):
    params = {
        "q": query,
        "api_key": serpapi_key,
        "engine": "google",
        "num": 3  # Limit results to top 3 for brevity
    }
    response = requests.get("https://serpapi.com/search", params=params)
    if response.status_code == 200:
        search_results = response.json().get("organic_results", [])
        return "\n".join([f"{result['title']}: {result['link']}" for result in search_results])
    return "Could not retrieve search results at this time."

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        prompt = data.get("prompt")
        if not prompt or not isinstance(prompt, str):
            return jsonify({"error": "Invalid or missing prompt"}), 400
            
        session_id = data.get("session_id", "default")
        if not isinstance(session_id, str):
            return jsonify({"error": "Invalid session_id format"}), 400

        # Check for the keyword "search" in the user prompt
        if "search" in prompt.lower():
            try:
                search_query = prompt.lower().replace("search", "").strip()
                search_results = call_serp_api(search_query)
                add_to_memory(session_id, "Assistant", search_results)
                return jsonify({"response": search_results})
            except Exception as e:
                print(f"Search error: {str(e)}")
                return jsonify({"error": "Search operation failed"}), 500

        # Add the user's prompt to memory
        add_to_memory(session_id, "User", prompt)

        # Build the conversation context
        conversation_history = get_recent_memory(session_id)
        conversation_context = (
            "You are Metis OS, a spatial agentic system specializing in geospatial and threat intelligence. "
            "Answer the user's questions directly and clearly. "
            "Do not repeat or echo the user's statements, and avoid creating fictional dialogue.\n\n"
        )
        
        for message in conversation_history:
            role = "User" if message['role'] == "User" else "Assistant"
            conversation_context += f"{role}: {message['message']}\n"

        # Run the prompt through the Ollama model
        full_prompt = f"{conversation_context}User: {prompt}\nAssistant:"
        response_text = llm.invoke(full_prompt)

        # Check for errors in response
        if response_text.startswith("Error:"):
            print(f"Model error: {response_text}")
            return jsonify({"error": response_text}), 500

        # Extract and validate response
        final_response = extract_assistant_response(response_text)
        if not final_response:
            return jsonify({"error": "Failed to generate valid response"}), 500

        # Add the assistant's response to memory
        add_to_memory(session_id, "Assistant", final_response)
        return jsonify({"response": final_response})

    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5004)
