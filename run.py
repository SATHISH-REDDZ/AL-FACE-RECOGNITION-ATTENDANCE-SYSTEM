#!/usr/bin/env python3
"""
AI Face Recognition Attendance & Business Studio Launcher
"""
import os
import sys
import config
import database
from face_engine import engine

def main():
    print("=" * 65)
    print("   AI FACE RECOGNITION ATTENDANCE & BUSINESS STUDIO")
    print("=" * 65)

    
    print("[1/3] Initializing SQLite database...")
    database.init_db()
    print(" -> Database ready at:", config.DB_PATH)

    print("[2/3] Loading Face Recognition Engine & Model...")
    engine.load_model()
    if engine.is_trained:
        print(" -> Model loaded successfully with trained face profiles.")
    else:
        print(" -> No trained model found yet. You can register students via the Web Dashboard.")

    # Check CLI arguments for --streamlit
    if "--streamlit" in sys.argv or "-s" in sys.argv:
        print("[3/3] Launching Streamlit AI Business Analytics Studio...")
        print(" -> Access Streamlit app at: http://localhost:8501")
        print("=" * 65)
        os.system(f"streamlit run {os.path.join(config.BASE_DIR, 'streamlit_app.py')}")
        return

    print("[3/3] Starting Flask Web Server & AI Studio...")
    print(f" -> Access Flask Web Dashboard at: http://localhost:{config.PORT}")
    print(f" -> Access AI Chat Studio tab at: http://localhost:{config.PORT}/chat")
    print(" -> Tip: Run 'python run.py --streamlit' or 'streamlit run streamlit_app.py' for Streamlit app.")
    print("=" * 65)

    from app import app
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)

if __name__ == '__main__':
    main()
