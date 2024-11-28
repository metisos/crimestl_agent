from flask import Flask, jsonify, render_template, request
from crime_agent import CrimeAgent
import logging
import json
import pandas as pd
import numpy as np
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
crime_agent = CrimeAgent()

# Initialize data on startup
try:
    crime_agent.analyze_csv('October2024.csv')
    logger.info("Successfully initialized crime data")
except Exception as e:
    logger.error(f"Error initializing crime data: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_crime_data')
def get_crime_data():
    try:
        # First analyze the data to ensure clusters are computed
        crime_agent.analyze_csv('October2024.csv')
        
        # Then read the analyzed data
        df = pd.read_csv('October2024.csv')
        
        # Convert date and extract temporal features
        df['IncidentDate'] = pd.to_datetime(df['IncidentDate'], format='%Y-%m-%d', errors='coerce')
        
        # Parse time and extract hour
        def extract_hour(time_str):
            try:
                if pd.isna(time_str):
                    return 0
                if isinstance(time_str, str):
                    time_parts = time_str.split(':')
                    if len(time_parts) >= 1:
                        hour = int(time_parts[0])
                        if 0 <= hour < 24:  # Validate hour is in valid range
                            return hour
                return 0
            except Exception as e:
                logger.error(f"Error extracting hour from {time_str}: {str(e)}")
                return 0

        # Extract temporal features
        df['Hour'] = df['OccurredFromTime'].apply(extract_hour)
        df['Year'] = df['IncidentDate'].dt.year
        df['DayOfWeek'] = df['IncidentDate'].dt.day_name()
        df['Month'] = df['IncidentDate'].dt.month_name()
        
        # Convert DataFrame to list of dictionaries
        crimes = []
        for _, row in df.iterrows():
            try:
                if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
                    continue
                    
                crime = {
                    'latitude': float(row['Latitude']),
                    'longitude': float(row['Longitude']),
                    'crime_type': str(row['Offense']) if not pd.isna(row['Offense']) else 'Unknown',
                    'category': str(row['Category']) if 'Category' in df.columns and not pd.isna(row['Category']) else 'Other',
                    'date': row['IncidentDate'].strftime('%Y-%m-%d') if not pd.isna(row['IncidentDate']) else 'Unknown',
                    'time': str(row['OccurredFromTime']),  # Keep original time string
                    'hour': int(row['Hour']),
                    'day_of_week': str(row['DayOfWeek']),
                    'month': str(row['Month']),
                    'year': int(row['Year']) if not pd.isna(row['Year']) else 0,
                    'neighborhood': str(row['Neighborhood']) if not pd.isna(row['Neighborhood']) else 'Unknown',
                    'cluster': int(row['Cluster']) if 'Cluster' in df.columns and not pd.isna(row['Cluster']) else 0,
                    'is_anomaly': bool(row['Anomaly']) if 'Anomaly' in df.columns and not pd.isna(row['Anomaly']) else False
                }
                crimes.append(crime)
            except Exception as e:
                logger.error(f"Error processing row: {str(e)}")
                continue
                
        return jsonify(crimes)
    except Exception as e:
        logger.error(f"Error in get_crime_data: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/get_crime_categories')
def get_crime_categories():
    """Get available crime categories"""
    return jsonify(list(crime_agent.crime_categories.keys()))

@app.route('/insights')
@app.route('/get_insights')  # Keep old route for backward compatibility
def get_insights():
    """Get insights from the database"""
    try:
        raw_insights = crime_agent.get_insights()
        # Transform insights into the format expected by frontend
        response = {
            'insights': [
                {
                    'id': insight['id'],
                    'text': insight['insight_text'],
                    'type': insight['insight_type'],
                    'confidence': insight['confidence'],
                    'timestamp': insight['timestamp'],
                    'metadata': insight['metadata'],
                    'feedback': insight['validation_feedback'],
                    'validated': insight['validated']
                }
                for insight in raw_insights
            ]
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error getting insights: {str(e)}")
        return jsonify({'insights': []})

@app.route('/temporal_stats')
@app.route('/get_temporal_stats')  # Keep old route for backward compatibility
def get_temporal_stats():
    try:
        # Get temporal patterns from database
        hourly_pattern = crime_agent.db.get_pattern('hourly') or {}
        daily_pattern = crime_agent.db.get_pattern('daily') or {}
        monthly_pattern = crime_agent.db.get_pattern('monthly') or {}
        
        # Convert pattern data from JSON strings if needed
        if isinstance(hourly_pattern.get('pattern_data'), str):
            hourly_pattern['pattern_data'] = json.loads(hourly_pattern['pattern_data'])
        if isinstance(daily_pattern.get('pattern_data'), str):
            daily_pattern['pattern_data'] = json.loads(daily_pattern['pattern_data'])
        if isinstance(monthly_pattern.get('pattern_data'), str):
            monthly_pattern['pattern_data'] = json.loads(monthly_pattern['pattern_data'])
            
        # Format the response to match frontend expectations
        response = {
            'temporal_patterns': {
                'hourly': hourly_pattern.get('pattern_data', {}).get('counts', {}),
                'daily': daily_pattern.get('pattern_data', {}).get('counts', {}),
                'monthly': monthly_pattern.get('pattern_data', {}).get('counts', {})
            },
            'metadata': {
                'hourly': {
                    'peak_hour': hourly_pattern.get('pattern_data', {}).get('peak_hour'),
                    'peak_count': hourly_pattern.get('pattern_data', {}).get('peak_count')
                },
                'daily': {
                    'busiest_day': daily_pattern.get('pattern_data', {}).get('busiest_day'),
                    'peak_count': daily_pattern.get('pattern_data', {}).get('peak_count')
                },
                'monthly': {
                    'busiest_month': monthly_pattern.get('pattern_data', {}).get('busiest_month'),
                    'peak_count': monthly_pattern.get('pattern_data', {}).get('peak_count')
                }
            }
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error getting temporal stats: {str(e)}")
        return jsonify({
            'temporal_patterns': {
                'hourly': {},
                'daily': {},
                'monthly': {}
            },
            'metadata': {
                'hourly': {'peak_hour': None, 'peak_count': 0},
                'daily': {'busiest_day': None, 'peak_count': 0},
                'monthly': {'busiest_month': None, 'peak_count': 0}
            }
        })

@app.route('/api/insights', methods=['GET'])
def get_all_insights():
    try:
        insights = crime_agent.db.get_insights(limit=10)
        if insights:
            # Format insights for display
            formatted_insights = []
            for insight in insights:
                formatted_insight = {
                    'text': insight['insight_text'],
                    'type': insight['insight_type'],
                    'confidence': float(insight['confidence']) if insight['confidence'] else 0.0,
                    'metadata': insight['metadata'] if insight['metadata'] else {},
                    'timestamp': insight['timestamp']
                }
                formatted_insights.append(formatted_insight)
            
            return jsonify({
                'status': 'success',
                'insights': formatted_insights
            })
        else:
            # If no insights, trigger analysis
            crime_agent.analyze_csv('October2024.csv')
            return jsonify({
                'status': 'success',
                'insights': [],
                'message': 'Analysis in progress, please try again shortly'
            })
    except Exception as e:
        logger.error(f"Error getting insights: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/insights/validate', methods=['POST'])
def validate_insight():
    try:
        data = request.get_json()
        if not data or 'insight_id' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing insight_id in request'
            }), 400

        insight_id = data['insight_id']
        feedback = data.get('feedback', '')
        validated = data.get('validated', False)

        success = crime_agent.db.validate_insight(insight_id, validated, feedback)
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Insight validation updated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update insight validation'
            }), 500
    except Exception as e:
        logger.error(f"Error validating insight: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/monitor/start')
def start_monitor():
    from monitor import monitor
    result = monitor.start()
    return jsonify({'status': 'Monitor started'})

@app.route('/monitor/stop')
def stop_monitor():
    from monitor import monitor
    result = monitor.stop()
    return jsonify({'status': 'Monitor stopped'})

@app.route('/monitor/status')
def monitor_status():
    from monitor import monitor
    status = {
        'running': monitor.running,
        'last_analysis': monitor.last_analysis.strftime('%Y-%m-%d %H:%M:%S') if monitor.last_analysis else None,
        'data_file': monitor.data_file
    }
    return jsonify(status)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'No question provided', 'success': False}), 400
            
        logger.info(f"Processing question: {question}")
        
        # Get direct answer from CSV data
        answer = crime_agent.query_csv_data(question)
        
        if not answer:
            return jsonify({
                'answer': "I apologize, but I couldn't find relevant information for your question. Please try asking something else.",
                'success': False
            })
        
        return jsonify({
            'answer': answer,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'answer': 'An error occurred while processing your question. Please try again.',
            'success': False
        }), 500

if __name__ == '__main__':
    try:
        # Import and start the monitor (it will run in the background)
        from monitor import monitor
        
        # Start the Flask app
        app.run(debug=True, port=5003)
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")
