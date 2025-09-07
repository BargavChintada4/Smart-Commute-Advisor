# Smart Commute & Air Quality Advisor

![Python](https://img.shields.io/badge/Python-3.9-blue.svg)
![Framework](https://img.shields.io/badge/Framework-Streamlit-red.svg)
![Deployment](https://img.shields.io/badge/Deployment-AWS%20ECS-orange.svg)
![Status](https://img.shields.io/badge/Status-Completed-green.svg)

A Streamlit web application designed to provide intelligent, real-time commute recommendations. This app helps users in metropolitan areas decide the best mode of transport by analyzing current traffic conditions, air quality, and weather forecasts, deployed as a fully containerized service on AWS.

---

## 🚀 Live Demo

The application is deployed and live on AWS ECS. You can access it here:

**[http://13.233.212.246:8501](http://13.233.212.246:8501)**


---

## ✨ Features

* **Multi-API Data Fusion:** Aggregates and synthesizes data in real-time from three distinct public APIs: Google Maps, World Air Quality Index (WAQI), and OpenWeatherMap.
* **Intelligent Commute Mode Comparison:** Provides a side-by-side comparison of `Driving` vs. `Public Transit` times.
* **Predictive Traffic Analysis:** Leverages Google's `duration_in_traffic` to calculate and display real-time traffic delays.
* **Environmental Insights:** Displays current Air Quality Index (AQI), the dominant pollutant, and the current temperature.
* **Weather Forecasting:** Includes a human-readable weather summary for the day and an hourly forecast chart for temperature and rain probability.
* **Advanced User Inputs:** Offers three ways to set origin and destination for maximum flexibility:
    * **Live GPS:** Uses the browser's geolocation to get the current position.
    * **Interactive Map:** Allows users to select a precise point on a map (powered by Folium).
    * **Manual Text Entry.**
* **Dynamic UI:** The report section is rendered conditionally, only showing the metrics for which data was successfully fetched.
* **Robust Error Handling:** API failures and invalid user inputs are handled silently in the backend to ensure a smooth user experience.

---

## 🛠️ Tech Stack & Architecture

This project was built as a modern, cloud-native web application.

* **Frontend:** Streamlit, Pandas, Folium (`streamlit-folium`), `streamlit-geolocation`
* **Backend / Data Orchestration:** Python, Requests
* **Deployment:** Docker, Docker Hub, AWS ECS (Fargate), AWS IAM, AWS Secrets Manager

### Architecture Flow

1.  A user interacts with the Streamlit frontend running in a Docker container.
2.  The Python backend receives the origin/destination and makes concurrent calls to the external APIs.
3.  **Geocoding:** City names are converted to coordinates for the weather API.
4.  **Data Fetching:**
    * **Google Maps API:** Provides driving and transit times, including traffic predictions.
    * **WAQI API:** Provides AQI data for the nearest station.
    * **OpenWeatherMap One Call API:** Provides current weather, summaries, and forecasts.
5.  The backend synthesizes the data through a rule-based recommendation engine.
6.  The final report and recommendation are displayed to the user.

---

## ⚙️ Setup and Local Installation

To run this project locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/Smart-Commute-Advisor.git](https://github.com/your-username/Smart-Commute-Advisor.git)
    cd Smart-Commute-Advisor
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create your secrets file:**
    * Create a folder named `.streamlit` in the project directory.
    * Inside it, create a file named `secrets.toml`.
    * Add your API keys to this file:
        ```toml
        # .streamlit/secrets.toml
        WAQI_API_TOKEN = "your_waqi_token_here"
        GOOGLE_MAPS_API_KEY = "your_google_maps_api_key_here"
        OPENWEATHER_API_KEY = "your_openweathermap_api_key_here"
        ```

5.  **Run the Streamlit application:**
    ```bash
    streamlit run app.py
    ```

---

## 🐳 Running with Docker

The application is fully containerized.

1.  **Build the Docker image:**
    ```bash
    docker build -t commute-advisor .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8501:8501 commute-advisor
    ```
    The application will be available at `http://localhost:8501`.

---
