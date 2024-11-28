# St. Louis Crime Intelligence Platform

An interactive crime data visualization and analysis platform for St. Louis, featuring temporal analysis, geographical mapping, and intelligent pattern detection.

## 🌟 Features

- **Interactive Crime Map**: Visualize crime incidents across St. Louis with dynamic filtering
- **Temporal Analysis**: Analyze crime patterns by hour, day, and month
- **Intelligent Clustering**: Automatic detection of crime hotspots and patterns
- **Real-time Monitoring**: Continuous analysis of crime data with automated insights
- **User-friendly Interface**: Modern, responsive design with intuitive controls

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Flask
- Pandas
- Other dependencies listed in `requirements.txt`

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/crimestl.git
cd crimestl
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python -m flask run --port 5002
```

4. Open your browser and navigate to `http://localhost:5002`

## 📊 Data Sources

The platform uses St. Louis crime data from official sources. The current implementation works with:
- Crime incident data in CSV format
- Required columns: IncidentDate, OccurredFromTime, Latitude, Longitude, Offense, Category, Neighborhood

## 🔧 Configuration

Key configuration options:
- Port: Default 5002 (configurable via command line)
- Data refresh interval: 300 seconds (configurable in monitor.py)
- Data source: `October2024.csv` (configurable in app.py)

## 🛠️ Project Structure

```
crimestl/
├── app.py              # Main Flask application
├── crime_agent.py      # Crime analysis and pattern detection
├── monitor.py          # Real-time data monitoring
├── database.py         # Data storage and retrieval
├── templates/          # HTML templates
│   └── index.html     # Main dashboard template
├── static/            # Static assets
└── requirements.txt   # Project dependencies
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- St. Louis Metropolitan Police Department for providing the crime data
- Contributors and maintainers of the open-source libraries used in this project

## 📧 Contact

Your Name - your.email@example.com
Project Link: https://github.com/yourusername/crimestl
