from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
import traceback

logger = logging.getLogger(__name__)
DEBUG = True

@csrf_exempt
@require_http_methods(["POST"])
def trigger_scraper(request):
    """Scraper trigger endpoint - pure mock for CI tests"""
    try:
        logger.info(f"Scraper trigger called - method: {request.method}")
        
        # Parse JSON body
        if request.body:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'Invalid JSON body',
                    'status': 'error'
                }, status=400)
        else:
            data = {}
        
        # Get parameters with defaults
        url = data.get('url', 'https://example.com')
        data_type = data.get('data_type', 'table')
        css_selector = data.get('css_selector', '')
        
        logger.info(f"Processing scrape request - URL: {url}, type: {data_type}")
        
        # Return success response without touching database
        return JsonResponse({
            'status': 'success',
            'message': 'Scraper triggered successfully',
            'task_id': 'mock-task-12345',
            'url': url,
            'data_type': data_type,
            'css_selector': css_selector
        }, status=200)
        
    except Exception as e:
        logger.error(f"Scraper trigger error: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)

def list_scraped_data(request):
    """List scraped data endpoint - pure mock without database"""
    # Return mock data without querying database
    return JsonResponse({
        'total': 0,
        'results': [],
        'page': 1,
        'page_size': 20
    }, status=200)

def scraper_targets(request):
    """Mock scraper targets endpoint"""
    return JsonResponse({
        'total': 0,
        'results': []
    }, status=200)