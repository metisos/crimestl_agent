import time
import threading
import logging
import pandas as pd
from datetime import datetime, timedelta
from crime_agent import CrimeAgent

logger = logging.getLogger(__name__)

class CrimeMonitor:
    def __init__(self, data_file='October2024.csv', analysis_interval=300):
        """
        Initialize the crime monitor
        :param data_file: CSV file containing crime data
        :param analysis_interval: How often to run analysis (in seconds)
        """
        self.data_file = data_file
        self.analysis_interval = analysis_interval
        self.crime_agent = CrimeAgent()
        self.last_analysis = None
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the monitoring process"""
        if self.running:
            logger.warning("Monitor is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Crime monitor started")
        
    def stop(self):
        """Stop the monitoring process"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Crime monitor stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                current_time = datetime.now()
                
                # Run analysis if it's the first time or if enough time has passed
                if (not self.last_analysis or 
                    (current_time - self.last_analysis).total_seconds() >= self.analysis_interval):
                    
                    logger.info("Starting scheduled crime data analysis")
                    
                    # Read and analyze the data
                    df = pd.read_csv(self.data_file)
                    
                    # Convert date and extract temporal features
                    df['IncidentDate'] = pd.to_datetime(df['IncidentDate'], errors='coerce')
                    
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
                    df['DayOfWeek'] = df['IncidentDate'].dt.day_name()
                    df['Month'] = df['IncidentDate'].dt.month_name()
                    df['Year'] = df['IncidentDate'].dt.year
                    
                    # Perform temporal analysis
                    self.crime_agent._analyze_temporal_patterns(df)
                    
                    # Analyze crime patterns
                    self.crime_agent._analyze_crime_patterns(df)
                    
                    # Analyze victim patterns
                    self.crime_agent._analyze_victim_patterns(df)
                    
                    # Generate AI-powered insights using the language model
                    self._generate_ai_insights(df)
                    
                    self.last_analysis = current_time
                    logger.info("Scheduled analysis completed")
                
                # Sleep for a short interval before checking again
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(30)  # On error, wait longer before retry
                continue
                
    def _generate_ai_insights(self, df):
        """Generate AI-powered insights using the language model"""
        try:
            # Get recent patterns
            hourly_pattern = self.crime_agent.db.get_pattern('hourly')
            daily_pattern = self.crime_agent.db.get_pattern('daily')
            monthly_pattern = self.crime_agent.db.get_pattern('monthly')
            crime_pattern = self.crime_agent.db.get_pattern('crime_types')
            location_pattern = self.crime_agent.db.get_pattern('locations')
            
            # Create a context for the AI
            context = {
                'total_crimes': len(df),
                'date_range': f"{df['Date'].min()} to {df['Date'].max()}",
                'hourly_pattern': hourly_pattern,
                'daily_pattern': daily_pattern,
                'monthly_pattern': monthly_pattern,
                'crime_pattern': crime_pattern,
                'location_pattern': location_pattern
            }
            
            # Generate insights using the language model
            prompt = f"""Analyze the following crime statistics and generate 3 key insights:
            Time period: {context['date_range']}
            Total crimes: {context['total_crimes']}
            
            Key patterns:
            - Most common crime type: {crime_pattern.get('counts', {}).get('top_crime', 'Unknown')}
            - Most affected location: {location_pattern.get('counts', {}).get('top_location', 'Unknown')}
            - Peak crime hour: {hourly_pattern.get('peak_hour', 'Unknown')}
            - Busiest day: {daily_pattern.get('busiest_day', 'Unknown')}
            
            Focus on:
            1. Emerging patterns
            2. Notable changes
            3. Public safety recommendations
            """
            
            response = self.crime_agent.llm(prompt)
            insights = response.split('\n')
            
            # Store AI-generated insights
            for insight in insights:
                if insight.strip():
                    self.crime_agent.db.add_insight(
                        insight_text=insight.strip(),
                        insight_type='ai_analysis',
                        confidence=0.85,
                        metadata={'generated_at': datetime.now().isoformat()}
                    )
            
            logger.info("Generated new AI insights")
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")

# Create and start the monitor when this module is imported
monitor = CrimeMonitor()
monitor.start()
