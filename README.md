# IMDb Top 250 Movie Parser
This script parses the top 250 movies from the IMDb website.
It gathers information about
the movies, the actors, and calculates the average rating of the movies in which each actor has appeared.

## Getting Started

### Prerequisites

#### Before running the script, you'll need to have the following installed:

    Python 3.x
    Google Sheets API credentials (in JSON format)

## Installation

1. Clone this repository:
```shell
git clone https://github.com/SashaKisliy/parse-top-imdb.git
cd parse-top-imdb
```
2. Create a virtual Python environment and activate it:
```shell
python -m venv .venv 
source .venv/bin/activate   # on macOS
.\.venv\Scripts\activate    # on Windows
```
3. Install the required dependencies:
```shell
pip install -r requirements.txt
```

## Running the Script

### Once everything is set up, you can run the script using the following command:
```shell
python parse.py
```

## Notes

### Make sure to place your Google Sheets API credentials JSON file in the root directory and update the script with the correct file name.
### The script is designed to run in headless mode and will not open any browser windows.


# Have a great day! 🎬😊