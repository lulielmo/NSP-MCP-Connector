"""
Local REST API Server for NSP MCP Connector
Exposes NSP functions via REST API for Azure Function
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv
from nsp_client import NSPClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Allow CORS for Azure Function

# Initialize NSP client
nsp_client = NSPClient(
    base_url=os.getenv('NSP_BASE_URL', 'http://localhost:1900/api/PublicApi/'),
    username=os.getenv('NSP_USERNAME', ''),
    password=os.getenv('NSP_PASSWORD', '')
)

@app.before_request
def authenticate_if_needed():
    """Authenticate against NSP if token is missing or expired"""
    # The NSPClient now handles token validation automatically
    # This is mainly for logging and monitoring
    token_info = nsp_client.get_token_info()
    if not token_info['has_token'] or token_info['is_expired']:
        logger.info("Token validation needed before request")
        if not nsp_client.ensure_valid_token():
            return jsonify({"error": "Authentication against NSP failed"}), 401

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    token_info = nsp_client.get_token_info()
    return jsonify({
        "status": "healthy",
        "service": "nsp-local-api",
        "authenticated": token_info['has_token'] and not token_info['is_expired'],
        "token_info": {
            "has_token": token_info['has_token'],
            "expires": token_info['expires'],
            "is_expired": token_info['is_expired']
        }
    })

@app.route('/api/token/status', methods=['GET'])
def token_status():
    """Get current token status for debugging"""
    token_info = nsp_client.get_token_info()
    return jsonify({
        "success": True,
        "data": token_info
    })

@app.route('/api/token/refresh', methods=['POST'])
def refresh_token():
    """Manually refresh authentication token"""
    try:
        logger.info("Manual token refresh requested")
        if nsp_client.authenticate():
            token_info = nsp_client.get_token_info()
            return jsonify({
                "success": True,
                "message": "Token refreshed successfully",
                "data": token_info
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to refresh token"
            }), 401
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/get_tickets', methods=['POST'])
def get_tickets():
    """Get tickets from NSP"""
    try:
        data = request.get_json() or {}
        page = data.get('page', 1)
        page_size = data.get('page_size', 15)
        filters = data.get('filters', {})
        
        logger.info(f"Fetching tickets: page={page}, page_size={page_size}")
        
        result = nsp_client.get_tickets(page, page_size, filters)
        
        return jsonify({
            "success": True,
            "data": result.get('Result', []),
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": result.get('TotalCount', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching tickets: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/get_ticket/<int:ticket_id>', methods=['GET'])
def get_ticket_by_id(ticket_id):
    """Get specific ticket by ID"""
    try:
        logger.info(f"Fetching ticket with ID: {ticket_id}")
        
        result = nsp_client.get_ticket_by_id(ticket_id)
        
        return jsonify({
            "success": True,
            "data": result.get('Result', {})
        })
        
    except Exception as e:
        logger.error(f"Error fetching ticket {ticket_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/create_ticket', methods=['POST'])
def create_ticket():
    """Create new ticket"""
    try:
        ticket_data = request.get_json()
        
        if not ticket_data:
            return jsonify({
                "success": False,
                "error": "No ticket data provided"
            }), 400
        
        logger.info("Creating new ticket")
        
        result = nsp_client.create_ticket(ticket_data)
        
        return jsonify({
            "success": True,
            "data": result.get('Result', {}),
            "message": "Ticket created"
        })
        
    except Exception as e:
        logger.error(f"Error creating ticket: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/update_ticket/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    """Update existing ticket"""
    try:
        updates = request.get_json()
        
        if not updates:
            return jsonify({
                "success": False,
                "error": "No update data provided"
            }), 400
        
        logger.info(f"Updating ticket {ticket_id}")
        
        result = nsp_client.update_ticket(ticket_id, updates)
        
        return jsonify({
            "success": True,
            "data": result.get('Result', {}),
            "message": "Ticket updated"
        })
        
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/search_entities', methods=['POST'])
def search_entities():
    """Search among entities"""
    try:
        data = request.get_json() or {}
        entity_type = data.get('entity_type', 'Ticket')
        query = data.get('query', '')
        page = data.get('page', 1)
        page_size = data.get('page_size', 15)
        
        if not query:
            return jsonify({
                "success": False,
                "error": "Search query required"
            }), 400
        
        logger.info(f"Searching for '{query}' in {entity_type}")
        
        result = nsp_client.search_entities(entity_type, query, page, page_size)
        
        return jsonify({
            "success": True,
            "data": result.get('Result', []),
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": result.get('TotalCount', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/get_entity_types', methods=['GET'])
def get_entity_types():
    """Get available entity types"""
    try:
        logger.info("Fetching entity types")
        
        result = nsp_client.get_entity_types()
        
        return jsonify({
            "success": True,
            "data": result.get('Result', [])
        })
        
    except Exception as e:
        logger.error(f"Error fetching entity types: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/get_entity_metadata/<entity_type>', methods=['GET'])
def get_entity_metadata(entity_type):
    """Get metadata for specific entity type"""
    try:
        logger.info(f"Fetching metadata for {entity_type}")
        
        result = nsp_client.get_entity_metadata(entity_type)
        
        return jsonify({
            "success": True,
            "data": result.get('Result', {})
        })
        
    except Exception as e:
        logger.error(f"Error fetching metadata for {entity_type}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/get_attachments/<entity_type>/<int:entity_id>', methods=['GET'])
def get_attachments(entity_type, entity_id):
    """Get attachments for entity"""
    try:
        logger.info(f"Fetching attachments for {entity_type} {entity_id}")
        
        result = nsp_client.get_attachments(entity_id, entity_type)
        
        return jsonify({
            "success": True,
            "data": result.get('Result', [])
        })
        
    except Exception as e:
        logger.error(f"Error fetching attachments: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting local NSP API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 