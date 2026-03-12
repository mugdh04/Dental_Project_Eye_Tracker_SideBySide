from flask import Flask, render_template, jsonify, request, redirect, url_for, session, send_file
import os
import sys
import threading
import time
import csv

# Check for required dependencies
try:
    from main import run_eye_tracker
except ImportError as e:
    print("=" * 60)
    print("ERROR: Missing required dependencies!")
    print("Please run: pip install -r requirements.txt")
    print(f"Details: {e}")
    print("=" * 60)
    sys.exit(1)

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.getcwd()

def get_image_counts():
    base_path = get_base_path()
    pre_path = os.path.join(base_path, "images", "pre")
    post_path = os.path.join(base_path, "images", "post")

    pre_count = len([f for f in os.listdir(pre_path) if f.endswith('.png')]) if os.path.exists(pre_path) else 0
    post_count = len([f for f in os.listdir(post_path) if f.endswith('.png')]) if os.path.exists(post_path) else 0

    return pre_count, post_count

def get_image_sets():
    base_path = get_base_path()
    pre_path = os.path.join(base_path, "images", "pre")
    post_path = os.path.join(base_path, "images", "post")

    if not os.path.exists(pre_path) or not os.path.exists(post_path):
        return []

    pre_images = {f.split('.')[0] for f in os.listdir(pre_path) if f.endswith('.png')}
    post_images = {f.split('.')[0] for f in os.listdir(post_path) if f.endswith('.png')}

    common = sorted(pre_images & post_images, key=lambda x: int(x))
    return common

@app.route('/')
def index():
    pre_count, post_count = get_image_counts()
    return render_template('index.html', pre_count=pre_count, post_count=post_count)

@app.route('/view-images')
def view_images():
    image_sets = get_image_sets()
    pre_count, post_count = get_image_counts()

    sets_data = []
    for img_id in image_sets:
        sets_data.append({
            'id': img_id,
            'pre_path': f'/image/pre/{img_id}.png',
            'post_path': f'/image/post/{img_id}.png'
        })

    return render_template('view_images.html',
                         image_sets=sets_data,
                         pre_count=pre_count,
                         post_count=post_count)

@app.route('/image/<img_type>/<filename>')
def serve_image(img_type, filename):
    """Serve images from the images folder"""
    if img_type not in ('pre', 'post'):
        return "Invalid image type", 400
    base_path = get_base_path()
    safe_filename = os.path.basename(filename)
    image_path = os.path.join(base_path, 'images', img_type, safe_filename)

    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/png')
    else:
        return "Image not found", 404

@app.route('/pre-flight-check')
def pre_flight_check():
    session['group'] = request.args.get('group', 'unknown')
    session['session_name'] = request.args.get('session', 'session')
    return render_template('pre_flight_check.html')

@app.route('/results/<filename>')
def view_results(filename):
    base_path = get_base_path()
    safe_filename = os.path.basename(filename)
    csv_path = os.path.join(base_path, 'logs', safe_filename)

    if not os.path.exists(csv_path):
        return "Results file not found", 404

    # Parse CSV file - side-by-side format (pre cols 0-3, post cols 5-8)
    sessions = []
    current_session = None
    summary_stats = {}
    reading_aois = False

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or not row[0]:
                reading_aois = False
                continue

            if row[0].startswith('Session -'):
                if current_session:
                    sessions.append(current_session)
                current_session = {
                    'name': row[0].replace('Session - ', '').replace(':', ''),
                    'pre_aois': [],
                    'post_aois': [],
                    'pre_first_focused': 'None',
                    'pre_most_focused': 'None',
                    'post_first_focused': 'None',
                    'post_most_focused': 'None'
                }
                reading_aois = False
            elif row[0] == 'AOI' and current_session:
                reading_aois = True
                continue
            elif row[0] == 'First Focused AOI' and current_session:
                reading_aois = False
                current_session['pre_first_focused'] = row[1] if len(row) > 1 else 'None'
                if len(row) > 6:
                    current_session['post_first_focused'] = row[6] if row[6] else 'None'
            elif row[0] == 'Most Focused AOI' and current_session:
                current_session['pre_most_focused'] = row[1] if len(row) > 1 else 'None'
                if len(row) > 6:
                    current_session['post_most_focused'] = row[6] if row[6] else 'None'
            elif row[0] == 'Total Blinks':
                summary_stats['total_blinks'] = row[1] if len(row) > 1 else '0'
            elif row[0] == 'Blink Rate (blinks/min)':
                summary_stats['blink_rate'] = row[1] if len(row) > 1 else '0'
            elif row[0].startswith('Pre Treatment') or row[0].startswith('Post Treatment'):
                continue
            elif reading_aois and current_session and len(row) >= 4:
                try:
                    current_session['pre_aois'].append({
                        'name': row[0],
                        'first_fixation': float(row[1]),
                        'total_fixation': float(row[2]),
                        'blinks': int(row[3])
                    })
                    if len(row) >= 9 and row[5]:
                        current_session['post_aois'].append({
                            'name': row[5],
                            'first_fixation': float(row[6]),
                            'total_fixation': float(row[7]),
                            'blinks': int(row[8])
                        })
                except Exception:
                    pass

    if current_session:
        sessions.append(current_session)

    return render_template('results.html',
                         sessions=sessions,
                         summary=summary_stats,
                         filename=safe_filename)

@app.route('/download-results/<filename>')
def download_results(filename):
    base_path = get_base_path()
    safe_filename = os.path.basename(filename)
    csv_path = os.path.join(base_path, 'logs', safe_filename)
    if not os.path.exists(csv_path):
        return "File not found", 404
    return send_file(csv_path, as_attachment=True)

@app.route('/start-tracking', methods=['POST'])
def start_tracking():
    try:
        group = session.get('group', 'unknown')
        session_name = session.get('session_name', 'session')

        # Read pointer visibility from request body
        data = request.get_json(silent=True) or {}
        show_pointer = '1' if data.get('show_pointer', False) else '0'

        # Store session info in file for main.py to read
        base_path = get_base_path()
        config_path = os.path.join(base_path, 'session_config.txt')
        with open(config_path, 'w') as f:
            f.write(f"{group}\n{session_name}\n{show_pointer}")

        # Run eye tracker in a separate thread
        def run_tracker():
            output_dir = os.path.join(base_path, "logs")
            image_dir = os.path.join(base_path, "images")
            os.makedirs(output_dir, exist_ok=True)

            from main import EyeTrackerApp
            EyeTrackerApp(output_folder=output_dir, image_folder=image_dir, show_csv=False)

        threading.Thread(target=run_tracker, daemon=True).start()

        return jsonify({'status': 'success', 'message': 'Eye tracking started!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/check-completion')
def check_completion():
    """Check if a new results file has been created"""
    base_path = get_base_path()
    logs_path = os.path.join(base_path, 'logs')

    if not os.path.exists(logs_path):
        return jsonify({'completed': False})

    csv_files = [f for f in os.listdir(logs_path) if f.endswith('.csv')]
    if not csv_files:
        return jsonify({'completed': False})

    latest_file = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(logs_path, f)))
    file_time = os.path.getmtime(os.path.join(logs_path, latest_file))

    if time.time() - file_time < 10:
        return jsonify({'completed': True, 'filename': latest_file})

    return jsonify({'completed': False})

@app.route('/api/image-status')
def image_status():
    try:
        pre_count, post_count = get_image_counts()
        return jsonify({
            'pre_count': pre_count,
            'post_count': post_count,
            'ready': pre_count == post_count and pre_count > 0
        })
    except Exception as e:
        print(f"Error in image_status: {e}")
        return jsonify({
            'pre_count': 0,
            'post_count': 0,
            'ready': False,
            'error': str(e)
        }), 500

@app.route('/api/results-list')
def results_list():
    """Return list of CSV result files"""
    base_path = get_base_path()
    logs_path = os.path.join(base_path, 'logs')
    if not os.path.exists(logs_path):
        return jsonify({'files': []})
    csv_files = sorted(
        [f for f in os.listdir(logs_path) if f.endswith('.csv')],
        key=lambda f: os.path.getmtime(os.path.join(logs_path, f)),
        reverse=True
    )
    return jsonify({'files': csv_files})

if __name__ == '__main__':
    base_path = get_base_path()
    os.makedirs(os.path.join(base_path, 'images', 'pre'), exist_ok=True)
    os.makedirs(os.path.join(base_path, 'images', 'post'), exist_ok=True)
    os.makedirs(os.path.join(base_path, 'logs'), exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=8001)
