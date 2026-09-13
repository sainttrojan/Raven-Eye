#!/bin/bash
# Start the radar loop in the background
python radar_loop.py &
# Start the Streamlit app
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
