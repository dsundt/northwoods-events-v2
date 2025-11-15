#!/usr/bin/env python3
"""
Web interface for managing curated event feeds.

This Flask application provides a web UI for:
- Browsing available events
- Creating and managing curated feeds
- Configuring preferences
- Generating feeds on-demand
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from flask import Flask, jsonify, render_template, request, send_from_directory

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.curated import process_curated_feeds
from src.main import main as run_pipeline
from src.util import slugify

app = Flask(__name__, 
            template_folder='../web/templates',
            static_folder='../web/static')

# Configuration
CURATED_CONFIG_PATH = os.getenv("CURATED_CONFIG_PATH", "config/curated.yaml")
REPORT_JSON_PATH = os.getenv("NW_REPORT_JSON", "public/report.json")
PUBLIC_DIR = os.getenv("PUBLIC_DIR", "public")


# ==================== Helper Functions ====================

def load_curated_config() -> List[Dict[str, Any]]:
    """Load curated feeds configuration from YAML."""
    if not os.path.exists(CURATED_CONFIG_PATH):
        return []
    
    try:
        with open(CURATED_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config if isinstance(config, list) else []
    except Exception as e:
        print(f"Error loading curated config: {e}")
        return []


def save_curated_config(config: List[Dict[str, Any]]) -> bool:
    """Save curated feeds configuration to YAML."""
    try:
        os.makedirs(os.path.dirname(CURATED_CONFIG_PATH), exist_ok=True)
        with open(CURATED_CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"Error saving curated config: {e}")
        return False


def load_events() -> List[Dict[str, Any]]:
    """Load all events from report.json."""
    if not os.path.exists(REPORT_JSON_PATH):
        return []
    
    try:
        with open(REPORT_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('normalized_events', [])
    except Exception as e:
        print(f"Error loading events: {e}")
        return []


def load_sources() -> List[Dict[str, Any]]:
    """Load source information from report.json."""
    if not os.path.exists(REPORT_JSON_PATH):
        return []
    
    try:
        with open(REPORT_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('source_logs', [])
    except Exception as e:
        print(f"Error loading sources: {e}")
        return []


def get_curated_feed_by_id(feed_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific curated feed by ID."""
    config = load_curated_config()
    for feed in config:
        if feed.get('id') == feed_id:
            return feed
    return None


# ==================== Web Routes ====================

@app.route('/')
def index():
    """Main page - curated feeds manager."""
    return render_template('index.html')


@app.route('/browse')
def browse():
    """Event browser page."""
    return render_template('browse.html')


@app.route('/feed/<feed_id>')
def feed_editor(feed_id):
    """Feed editor page."""
    return render_template('feed_editor.html', feed_id=feed_id)


@app.route('/new-feed')
def new_feed():
    """New feed creation page."""
    return render_template('feed_editor.html', feed_id='new')


# ==================== API Routes ====================

@app.route('/api/events')
def api_events():
    """Get all available events."""
    try:
        events = load_events()
        
        # Apply filters if provided
        keyword = request.args.get('keyword', '').lower()
        source = request.args.get('source', '').lower()
        location = request.args.get('location', '').lower()
        
        filtered_events = events
        
        if keyword:
            filtered_events = [
                e for e in filtered_events
                if keyword in (e.get('title') or '').lower() or
                   keyword in (e.get('location') or '').lower()
            ]
        
        if source:
            filtered_events = [
                e for e in filtered_events
                if source in (e.get('source') or '').lower()
            ]
        
        if location:
            filtered_events = [
                e for e in filtered_events
                if location in (e.get('location') or '').lower()
            ]
        
        return jsonify({
            'success': True,
            'total': len(events),
            'filtered': len(filtered_events),
            'events': filtered_events
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sources')
def api_sources():
    """Get all available sources."""
    try:
        sources = load_sources()
        return jsonify({
            'success': True,
            'sources': sources
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/feeds')
def api_feeds():
    """Get all curated feeds."""
    try:
        config = load_curated_config()
        
        # Load report to get stats
        report_data = {}
        if os.path.exists(REPORT_JSON_PATH):
            with open(REPORT_JSON_PATH, 'r', encoding='utf-8') as f:
                report = json.load(f)
                curated_feeds = report.get('curated_feeds', {})
                for feed in curated_feeds.get('feeds', []):
                    report_data[feed.get('id')] = feed
        
        # Merge config with stats
        feeds_with_stats = []
        for feed in config:
            feed_copy = dict(feed)
            feed_id = feed.get('id')
            if feed_id in report_data:
                feed_copy['stats'] = report_data[feed_id]
            feeds_with_stats.append(feed_copy)
        
        return jsonify({
            'success': True,
            'feeds': feeds_with_stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/feeds/<feed_id>')
def api_feed_get(feed_id):
    """Get a specific curated feed."""
    try:
        feed = get_curated_feed_by_id(feed_id)
        if feed:
            return jsonify({'success': True, 'feed': feed})
        else:
            return jsonify({'success': False, 'error': 'Feed not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/feeds', methods=['POST'])
def api_feed_create():
    """Create a new curated feed."""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('id') or not data.get('name'):
            return jsonify({'success': False, 'error': 'Missing required fields: id, name'}), 400
        
        # Load existing config
        config = load_curated_config()
        
        # Check for duplicate ID
        if any(f.get('id') == data.get('id') for f in config):
            return jsonify({'success': False, 'error': 'Feed ID already exists'}), 400
        
        # Create new feed
        new_feed = {
            'id': data.get('id'),
            'name': data.get('name'),
            'enabled': data.get('enabled', True),
            'selected_events': data.get('selected_events', []),
            'preferences': data.get('preferences', {})
        }
        
        config.append(new_feed)
        
        # Save config
        if save_curated_config(config):
            return jsonify({'success': True, 'feed': new_feed})
        else:
            return jsonify({'success': False, 'error': 'Failed to save config'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/feeds/<feed_id>', methods=['PUT'])
def api_feed_update(feed_id):
    """Update a curated feed."""
    try:
        data = request.json
        config = load_curated_config()
        
        # Find and update feed
        feed_found = False
        for i, feed in enumerate(config):
            if feed.get('id') == feed_id:
                # Update fields
                config[i]['name'] = data.get('name', feed.get('name'))
                config[i]['enabled'] = data.get('enabled', feed.get('enabled'))
                config[i]['selected_events'] = data.get('selected_events', feed.get('selected_events', []))
                config[i]['preferences'] = data.get('preferences', feed.get('preferences', {}))
                feed_found = True
                break
        
        if not feed_found:
            return jsonify({'success': False, 'error': 'Feed not found'}), 404
        
        # Save config
        if save_curated_config(config):
            return jsonify({'success': True, 'feed': config[i]})
        else:
            return jsonify({'success': False, 'error': 'Failed to save config'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/feeds/<feed_id>', methods=['DELETE'])
def api_feed_delete(feed_id):
    """Delete a curated feed."""
    try:
        config = load_curated_config()
        
        # Filter out the feed to delete
        new_config = [f for f in config if f.get('id') != feed_id]
        
        if len(new_config) == len(config):
            return jsonify({'success': False, 'error': 'Feed not found'}), 404
        
        # Save config
        if save_curated_config(new_config):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to save config'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """Generate curated feeds on-demand."""
    try:
        data = request.json or {}
        feed_id = data.get('feed_id')
        
        # Load all events
        events = load_events()
        
        if feed_id:
            # Generate specific feed
            config = load_curated_config()
            feed_config = next((f for f in config if f.get('id') == feed_id), None)
            
            if not feed_config:
                return jsonify({'success': False, 'error': 'Feed not found'}), 404
            
            # Process this one feed
            results = process_curated_feeds(
                events,
                config_path=CURATED_CONFIG_PATH,
                output_dir=os.path.join(PUBLIC_DIR, "curated")
            )
            
            return jsonify({
                'success': True,
                'message': f'Generated feed: {feed_id}',
                'results': results
            })
        else:
            # Generate all feeds
            results = process_curated_feeds(
                events,
                config_path=CURATED_CONFIG_PATH,
                output_dir=os.path.join(PUBLIC_DIR, "curated")
            )
            
            return jsonify({
                'success': True,
                'message': 'Generated all curated feeds',
                'results': results
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/pipeline/run', methods=['POST'])
def api_pipeline_run():
    """Run the full pipeline (fetch events + generate curated feeds)."""
    try:
        # Run the main pipeline in a subprocess to avoid blocking
        import subprocess
        import threading
        
        def run_in_background():
            try:
                subprocess.run([sys.executable, '-m', 'src.main'], 
                             cwd=os.path.dirname(os.path.dirname(__file__)),
                             check=True)
            except Exception as e:
                print(f"Pipeline error: {e}")
        
        thread = threading.Thread(target=run_in_background)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Pipeline started in background. Check report.json for results.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/report')
def api_report():
    """Get the latest pipeline report."""
    try:
        if not os.path.exists(REPORT_JSON_PATH):
            return jsonify({'success': False, 'error': 'No report available'}), 404
        
        with open(REPORT_JSON_PATH, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Static Files ====================

@app.route('/curated/<path:filename>')
def serve_curated(filename):
    """Serve generated curated ICS files."""
    return send_from_directory(os.path.join(PUBLIC_DIR, 'curated'), filename)


# ==================== Main ====================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Northwoods Events Web Interface on http://localhost:{port}")
    print(f"Curated config: {CURATED_CONFIG_PATH}")
    print(f"Report path: {REPORT_JSON_PATH}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
