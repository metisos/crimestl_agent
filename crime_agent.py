import pandas as pd
import numpy as np
from datetime import datetime
from database import InsightDatabase
import logging
import subprocess  # Added for Ollama model

logger = logging.getLogger(__name__)

class OllamaLocalModel:
    """Class to invoke the local Ollama model using CLI commands."""
    def __init__(self, model="llama3.2"):
        self.model = model
    
    def invoke(self, prompt):
        """Generate a response from the Ollama model using the CLI."""
        try:
            # Limit prompt length to 4000 characters
            if len(prompt) > 4000:
                prompt = prompt[:3900] + "... [truncated for length]"
            
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"Ollama error: {e.stderr}")
            return f"Error: {e.stderr}"

class CrimeAgent:
    def __init__(self, csv_file='October2024.csv'):
        """Initialize the CrimeAgent with database connection"""
        self.db = InsightDatabase()  # Initialize database connection
        self.csv_file = csv_file
        self.current_data = None
        self.ollama = OllamaLocalModel()  # Initialize Ollama model
        self.crime_categories = {
            'Violent Crimes': [
                'HOMICIDE', 'ASSAULT', 'ROBBERY', 'AGGRAVATED ASSAULT', 
                'WEAPONS OFFENSE', 'CARJACKING'
            ],
            'Property Crimes': [
                'BURGLARY', 'LARCENY', 'MOTOR VEHICLE THEFT', 'ARSON',
                'THEFT', 'STOLEN VEHICLE', 'VANDALISM'
            ],
            'Drug Crimes': [
                'DRUG ABUSE', 'DRUG DISTRIBUTION', 'DRUG POSSESSION'
            ],
            'Public Order': [
                'DISORDERLY CONDUCT', 'PUBLIC INTOXICATION',
                'TRESPASSING', 'LOITERING'
            ],
            'Other': [
                'OTHER OFFENSES', 'MISCELLANEOUS'
            ]
        }
        
    def analyze_csv(self, file_path: str):
        """Analyze crime data from CSV file and store insights"""
        try:
            logger.info(f"Starting analysis of {file_path}")
            df = pd.read_csv(file_path)
            self.current_data = df
            
            # Ensure required columns exist
            required_columns = {
                'OccurredFromTime': 'time',
                'IncidentDate': 'date',
                'Description': 'description',
                'Neighborhood': 'location',
                'Offense': 'type'
            }
            
            # Create missing columns with default values
            for col, default in required_columns.items():
                if col not in df.columns:
                    logger.warning(f"Missing column {col}, creating with default values")
                    df[col] = f"Unknown {default}"
            
            # Process temporal data
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

            # Convert date and extract temporal features
            df['IncidentDate'] = pd.to_datetime(df['IncidentDate'], errors='coerce')
            df['Hour'] = df['OccurredFromTime'].apply(extract_hour)
            df['DayOfWeek'] = df['IncidentDate'].dt.day_name()
            df['Month'] = df['IncidentDate'].dt.month_name()
            df['Year'] = df['IncidentDate'].dt.year
            
            # Fill NaN values
            df['DayOfWeek'] = df['DayOfWeek'].fillna('Unknown')
            df['Month'] = df['Month'].fillna('Unknown')
            df['Description'] = df['Description'].fillna('Unknown')
            df['Neighborhood'] = df['Neighborhood'].fillna('Unknown')
            df['Offense'] = df['Offense'].fillna('Unknown')
            
            self._analyze_temporal_patterns(df)
            self._analyze_crime_patterns(df)
            self._analyze_victim_patterns(df)
            self._generate_intelligence_report(df)
            
            logger.info("Analysis completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in analyze_csv: {str(e)}")
            return False
            
    def _analyze_temporal_patterns(self, df):
        """Analyze temporal patterns in the crime data"""
        try:
            # Ensure datetime columns are properly formatted
            if not pd.api.types.is_datetime64_any_dtype(df['IncidentDate']):
                df['IncidentDate'] = pd.to_datetime(df['IncidentDate'], errors='coerce')
            
            # Extract temporal features
            df['DayOfWeek'] = df['IncidentDate'].dt.day_name()
            df['Month'] = df['IncidentDate'].dt.month_name()
            
            # Get hourly crime counts
            hourly_counts = df['Hour'].value_counts().sort_index()
            
            # Ensure we have all 24 hours with at least 0 count
            all_hours = pd.Series(0, index=range(24))
            hourly_counts = hourly_counts.add(all_hours, fill_value=0)
            hourly_counts = hourly_counts.sort_index()
            
            peak_hour = int(hourly_counts.idxmax())
            peak_count = int(hourly_counts.max())
            
            hourly_data = {
                'counts': {str(k).zfill(2): int(v) for k, v in hourly_counts.to_dict().items()},
                'peak_hour': str(peak_hour).zfill(2),
                'peak_count': peak_count
            }
            
            # Store the pattern
            self.db.store_pattern('hourly', hourly_data)
            
            logger.info(f"Temporal analysis completed. Peak hour: {peak_hour}:00 with {peak_count} incidents")
            
        except Exception as e:
            logger.error(f"Error in temporal pattern analysis: {str(e)}")

    def _analyze_crime_patterns(self, df):
        """Analyze and store crime patterns"""
        try:
            # Crime type analysis
            crime_counts = df['Description'].value_counts()
            top_crimes = crime_counts.head(5)
            
            pattern_data = {
                'counts': {str(k): int(v) for k, v in crime_counts.head(10).to_dict().items()},
                'top_crime': str(top_crimes.index[0]),
                'top_count': int(top_crimes.iloc[0])
            }
            
            self.db.add_pattern('crime_types', pattern_data, confidence=0.95)
            
            # Add insight for each top crime type
            for crime_type, count in top_crimes.items():
                self.db.add_insight(
                    insight_text=f"{crime_type}: {count} incidents reported",
                    insight_type='crime_pattern',
                    confidence=0.95,
                    metadata={'crime_type': str(crime_type), 'count': int(count)}
                )
            
            # Location analysis
            location_counts = df['Neighborhood'].value_counts()
            top_locations = location_counts.head(5)
            
            location_data = {
                'counts': {str(k): int(v) for k, v in location_counts.head(10).to_dict().items()},
                'top_location': str(top_locations.index[0]),
                'top_count': int(top_locations.iloc[0])
            }
            
            self.db.add_pattern('locations', location_data, confidence=0.9)
            
            # Add insight for each top location
            for location, count in top_locations.items():
                self.db.add_insight(
                    insight_text=f"{location} has {count} reported incidents",
                    insight_type='location_pattern',
                    confidence=0.9,
                    metadata={'location': str(location), 'count': int(count)}
                )
            
        except Exception as e:
            logger.error(f"Error in crime pattern analysis: {str(e)}")

    def _analyze_victim_patterns(self, df):
        """Analyze victim patterns"""
        try:
            # Add some basic victim-related insights
            self.db.add_insight(
                insight_text="Analyzing victim patterns to identify vulnerable populations",
                insight_type='victim_pattern',
                confidence=0.7,
                metadata={'analysis_type': 'demographic'}
            )
            
            self.db.add_insight(
                insight_text="Monitoring repeat victimization patterns",
                insight_type='victim_pattern',
                confidence=0.7,
                metadata={'analysis_type': 'repeat_victimization'}
            )
            
        except Exception as e:
            logger.error(f"Error in victim pattern analysis: {str(e)}")

    def _generate_intelligence_report(self, df):
        """Generate comprehensive intelligence report"""
        try:
            # Add overall insights about the data
            total_incidents = len(df)
            date_range = f"{df['IncidentDate'].min().strftime('%Y-%m-%d')} to {df['IncidentDate'].max().strftime('%Y-%m-%d')}"
            
            self.db.add_insight(
                insight_text=f"Analyzed {total_incidents} incidents from {date_range}",
                insight_type='summary',
                confidence=1.0,
                metadata={'total_incidents': total_incidents, 'date_range': date_range}
            )
            
            # Add insights about data quality
            missing_locations = df['Neighborhood'].isna().sum()
            if missing_locations > 0:
                self.db.add_insight(
                    insight_text=f"Data quality issue: {missing_locations} incidents have missing location information",
                    insight_type='data_quality',
                    confidence=1.0,
                    metadata={'missing_locations': int(missing_locations)}
                )
            
        except Exception as e:
            logger.error(f"Error generating intelligence report: {str(e)}")

    def query_csv_data(self, user_query):
        """Query the CSV data directly based on user questions"""
        try:
            if self.current_data is None:
                self.analyze_csv(self.csv_file)
                
            if self.current_data is None:
                return "Error: Unable to load crime data"
                
            df = self.current_data.copy()
            df['Date_Time'] = pd.to_datetime(df['IncidentDate'])
            
            # Process the query to understand intent
            query = user_query.lower()
            
            # Location/Area related queries
            if any(word in query for word in ['area', 'where', 'location', 'neighborhood', 'place', 'district', 'region', 'zone', 'highest', 'dangerous']):
                hood_counts = df['Neighborhood'].value_counts()
                top_hoods = hood_counts.head(5)
                total_crimes = len(df)
                
                response = "Crime Analysis by Neighborhood:\n\n"
                response += "Top 5 Areas with Highest Crime Rates:\n"
                for hood, count in top_hoods.items():
                    percentage = (count / total_crimes) * 100
                    response += f"- {hood}: {count} incidents ({percentage:.1f}% of total crimes)\n"
                    
                # Add specific crime types for the highest crime area
                worst_hood = top_hoods.index[0]
                hood_crimes = df[df['Neighborhood'] == worst_hood]['Offense'].value_counts().head(3)
                
                response += f"\nMost Common Crimes in {worst_hood}:\n"
                for crime, count in hood_crimes.items():
                    response += f"- {crime}: {count} incidents\n"
                    
                return response.strip()
            
            # Crime type related queries
            if any(word in query for word in ['crime', 'offense', 'incident', 'common', 'frequent', 'type']):
                crime_counts = df['Offense'].value_counts()
                top_crimes = crime_counts.head(5)
                total_crimes = len(df)
                
                response = "Crime Type Analysis:\n\n"
                response += "Top 5 Most Common Crimes:\n"
                for crime, count in top_crimes.items():
                    percentage = (count / total_crimes) * 100
                    response += f"- {crime}: {count} incidents ({percentage:.1f}% of total)\n"
                
                # Add time patterns for the most common crime
                most_common = top_crimes.index[0]
                common_crime_df = df[df['Offense'] == most_common]
                peak_hour = common_crime_df['Hour'].mode()[0]
                peak_day = common_crime_df['DayOfWeek'].mode()[0]
                
                response += f"\nPattern for {most_common}:\n"
                response += f"- Most common on: {peak_day}\n"
                response += f"- Peak hour: {int(peak_hour):02d}:00"
                
                return response.strip()
            
            # Time related queries
            if any(word in query for word in ['time', 'hour', 'day', 'when', 'pattern']):
                hour_counts = df['Hour'].value_counts().sort_index()
                day_counts = df['DayOfWeek'].value_counts()
                
                response = "Temporal Crime Patterns:\n\n"
                
                # Daily patterns
                response += "Crime by Day of Week:\n"
                for day, count in day_counts.items():
                    response += f"- {day}: {count} incidents\n"
                
                # Hourly patterns - show all hours with their counts
                response += "\nCrime by Hour (24-hour format):\n"
                for hour in range(24):
                    count = hour_counts.get(hour, 0)  # Get count or 0 if hour not present
                    response += f"- {hour:02d}:00: {count} incidents\n"
                
                # Peak hour analysis
                peak_hour = int(hour_counts.idxmax())
                peak_count = hour_counts.max()
                response += f"\nPeak Activity:\n"
                response += f"- Highest activity: {peak_hour:02d}:00 ({peak_count} incidents)\n"
                
                # Add night vs day comparison
                night_hours = set([18,19,20,21,22,23,0,1,2,3,4,5])
                day_hours = set([6,7,8,9,10,11,12,13,14,15,16,17])
                night_crimes = df[df['Hour'].isin(night_hours)].shape[0]
                day_crimes = df[df['Hour'].isin(day_hours)].shape[0]
                total_crimes = night_crimes + day_crimes
                
                response += f"\nDay vs Night Comparison:\n"
                response += f"- Daytime (6:00-17:59): {day_crimes} incidents ({(day_crimes/total_crimes)*100:.1f}% of total crimes)\n"
                response += f"- Nighttime (18:00-5:59): {night_crimes} incidents ({(night_crimes/total_crimes)*100:.1f}%)"
                
                return response.strip()
            
            # Weapon/Safety related queries
            if any(word in query for word in ['weapon', 'gun', 'firearm', 'armed', 'dangerous']):
                armed_incidents = df[df['FirearmUsed'] == 'Yes']
                total_armed = len(armed_incidents)
                
                response = "Firearm-Related Crime Analysis:\n\n"
                response += f"Total firearm-related incidents: {total_armed}\n\n"
                
                # Types of armed crimes
                armed_types = armed_incidents['Offense'].value_counts().head(5)
                response += "Most Common Armed Incidents:\n"
                for crime, count in armed_types.items():
                    response += f"- {crime}: {count} incidents\n"
                
                # Locations of armed crimes
                armed_areas = armed_incidents['Neighborhood'].value_counts().head(3)
                response += "\nAreas with Most Armed Incidents:\n"
                for area, count in armed_areas.items():
                    response += f"- {area}: {count} incidents\n"
                
                return response.strip()
            
            # If asking for a report or general stats
            if any(word in query for word in ['report', 'summary', 'overview', 'statistics', 'stats', 'analysis']):
                total_incidents = len(df)
                date_range = f"{df['Date_Time'].min().strftime('%Y-%m-%d')} to {df['Date_Time'].max().strftime('%Y-%m-%d')}"
                
                # Get top crimes
                top_crimes = df['Offense'].value_counts().head(5)
                
                # Get top neighborhoods
                top_neighborhoods = df['Neighborhood'].value_counts().head(5)
                
                # Get time analysis
                hour_counts = df['Hour'].value_counts()
                peak_hour = hour_counts.idxmax()
                
                # Get day of week analysis
                day_counts = df['DayOfWeek'].value_counts()
                busiest_day = day_counts.index[0]
                
                # Get firearm statistics
                firearm_incidents = df[df['FirearmUsed'] == 'Yes']
                
                # Generate comprehensive report
                report = f"St. Louis Crime Analysis Report ({date_range})\n"
                report += f"==========================================\n\n"
                report += f"Total Incidents: {total_incidents}\n\n"
                
                report += "Most Common Crime Types:\n"
                report += "----------------------\n"
                for crime, count in top_crimes.items():
                    percentage = (count / total_incidents) * 100
                    report += f"- {crime}: {count} incidents ({percentage:.1f}% of total crimes)\n"
                
                report += "\nMost Affected Neighborhoods:\n"
                report += "-------------------------\n"
                for hood, count in top_neighborhoods.items():
                    percentage = (count / total_incidents) * 100
                    report += f"- {hood}: {count} incidents ({percentage:.1f}% of total crimes)\n"
                
                report += f"\nTemporal Patterns:\n"
                report += f"----------------\n"
                report += f"- Peak Activity Hour: {int(peak_hour):02d}:00\n"
                report += f"- Busiest Day: {busiest_day}\n"
                
                # Add day vs night comparison
                night_hours = set([18,19,20,21,22,23,0,1,2,3,4,5])
                day_hours = set([6,7,8,9,10,11,12,13,14,15,16,17])
                night_crimes = df[df['Hour'].isin(night_hours)].shape[0]
                day_crimes = df[df['Hour'].isin(day_hours)].shape[0]
                report += f"- Daytime Incidents (6:00-17:59): {day_crimes}\n"
                report += f"- Nighttime Incidents (18:00-5:59): {night_crimes}\n"
                
                if len(firearm_incidents) > 0:
                    report += f"\nFirearm-Related Incidents:\n"
                    report += f"----------------------\n"
                    report += f"Total firearm-related incidents: {len(firearm_incidents)}\n"
                    firearm_pct = (len(firearm_incidents) / total_incidents) * 100
                    report += f"Percentage of total crimes: {firearm_pct:.1f}%"
                
                return report.strip()
            
            # Default response with more natural suggestions
            return ("I can help you analyze St. Louis crime data. Try asking about:\n\n"
                   "- Where do most crimes occur?\n"
                   "- What are the most dangerous areas?\n"
                   "- What types of crimes are most common?\n"
                   "- When do most crimes happen?\n"
                   "- How many crimes involve weapons?\n"
                   "- Can you give me a complete crime report?\n\n"
                   "Feel free to ask in your own words!")
            
        except Exception as e:
            logger.error(f"Error in query_csv_data: {str(e)}")
            return ("I apologize, but I encountered an error while analyzing the data. "
                   "Please try rephrasing your question or ask for a specific aspect of crime data.")
    
    def answer_question(self, question: str) -> str:
        """Answer questions about crime patterns and insights"""
        try:
            # First try to get answer directly from CSV data
            data_answer = self.query_csv_data(question)
            
            # Use Ollama to enhance the answer with insights
            prompt = f"""As a crime analysis AI assistant, analyze this crime data and provide additional insights:

Question: {question}

Data Analysis:
{data_answer}

Please provide additional insights, patterns, or recommendations based on this data.
Keep your response focused and relevant to public safety."""

            ollama_insights = self.ollama.invoke(prompt)
            
            # Combine both answers
            full_answer = f"{data_answer}\n\nAdditional Insights:\n{ollama_insights}"
            return full_answer
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return "I apologize, but I encountered an error while processing your question. Please try asking in a different way."

    def get_insights(self, limit=10, insight_type=None):
        """Get insights from the database"""
        return self.db.get_insights(limit, insight_type)
        
    def get_patterns(self, pattern_type=None, min_frequency=None):
        """Get patterns from the database"""
        return self.db.get_patterns(pattern_type, min_frequency)
        
    def validate_insight(self, insight_id: int, is_valid: bool, feedback: str = None):
        """Validate an insight"""
        return self.db.validate_insight(insight_id, is_valid, feedback)
