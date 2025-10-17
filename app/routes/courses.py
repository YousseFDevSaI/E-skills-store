from flask import Blueprint, render_template, current_app, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
import requests
from urllib.parse import urljoin
import os
import traceback
import logging
from ..models.user import User
from ..models.course import Course
from ..models.enrollment import Enrollment
from ..utils.edx_api import OpenEdxAPI
from .. import db

logger = logging.getLogger(__name__)

courses_bp = Blueprint('courses', __name__)

@courses_bp.route('/')
def index():
    """List all available courses"""
    try:
        # Import OpenEdxAPI only when needed
        api = OpenEdxAPI()
        
        # Get page from query parameters
        page = request.args.get('page', 1, type=int)
        page_size = 12
        
        # Get courses from OpenEdX API
        response = api.get_courses(page=page, page_size=page_size)
        
        if response and 'results' in response:
            courses = response['results']
            total = len(courses)  # Since we're not getting total from API
            logger.info(f"Successfully fetched {len(courses)} courses")
        else:
            courses = []
            total = 0
            logger.warning("No courses found from OpenEdX API")
            
        # Get user's enrolled courses if logged in
        enrolled_courses = []
        if current_user.is_authenticated:
            enrolled_courses = current_user.get_enrolled_courses()
            
        return render_template('courses/index.html',
                             courses=courses,
                             enrolled_courses=enrolled_courses,
                             pagination={
                                 'page': page,
                                 'page_size': page_size,
                                 'total': total
                             })
                             
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}")
        return render_template('courses/index.html',
                             courses=[],
                             enrolled_courses=[],
                             pagination={
                                 'page': 1,
                                 'page_size': 12,
                                 'total': 0
                             })

@courses_bp.route('/<course_id>')
def detail(course_id):
    """Course detail page"""
    try:
        # Format course ID if needed
        if not course_id.startswith('course-v1:'):
            course_id = f'course-v1:{course_id}'
            
        logger.info(f"Fetching course details for ID: {course_id}")
        
        # Get course details from OpenEdX API
        api = OpenEdxAPI()
        
        # First try the catalog API
        course = api.get_course_details(course_id)
        
        if not course:
            # If catalog API fails, try the mobile API
            logger.info(f"Trying mobile API for course {course_id}")
            mobile_url = f"{api.base_url}/api/mobile/v0.5/course_info/{course_id}"
            headers = api._get_auth_headers()
            
            response = api.session.get(mobile_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                course = response.json()
                logger.info(f"Successfully fetched course details from mobile API for {course_id}")
            else:
                logger.error(f"Failed to fetch course details from mobile API: {response.status_code}")
                return render_template('courses/detail.html', error="Course not found")
        
        # Check if user is enrolled
        is_enrolled = False
        if current_user.is_authenticated:
            is_enrolled = current_user.is_enrolled(course_id)
            logger.info(f"User {current_user.username} enrollment status for {course_id}: {is_enrolled}")
        
        # Ensure all required fields are present
        course.update({
            'id': course_id,  # Add the course ID
            'name': course.get('name', 'Course'),
            'short_description': course.get('short_description', 'No description available.'),
            'overview': course.get('overview', 'No overview available.'),
            'prerequisites': course.get('prerequisites', 'No prerequisites.'),
            'org': course.get('org', 'Organization'),
            'number': course.get('number', 'Course Number'),
            'start_display': course.get('start_display', 'Not specified'),
            'pacing': course.get('pacing', 'Self-paced'),
            'effort': course.get('effort', 'Not specified'),
            'media': course.get('media', {}),
            'price': course.get('price', 0),
            'currency': course.get('currency', 'USD'),
            'mobile_available': course.get('mobile_available', True)
        })
        
        return render_template('courses/detail.html', 
                             course=course,
                             is_enrolled=is_enrolled)
                             
    except Exception as e:
        logger.error(f"Error loading course details: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return render_template('courses/detail.html', error="Error loading course details")

@courses_bp.route('/<course_id>/enroll', methods=['POST'])
@login_required
def enroll(course_id):
    """Enroll in a course"""
    try:
        # Get course details from OpenEdX API
        api = OpenEdxAPI()
        course = api.get_course(course_id)
        
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('courses.index'))
            
        # Check if user is already enrolled
        if current_user.is_enrolled(course_id):
            flash('You are already enrolled in this course', 'info')
            return redirect(url_for('courses.detail', course_id=course_id))
            
        # Proceed with enrollment
        success = ""
        success, error = api.enroll_user(current_user.username, course_id)
        
        if success:
            flash('Successfully enrolled in course', 'success')
        elif success == "":
            pass
        else:
            flash(f'Error enrolling in course: {error}', 'error')
            
        return redirect(url_for('courses.detail', course_id=course_id))
        
    except Exception as e:
        logger.error(f"Error enrolling in course: {str(e)}")
        flash('Error enrolling in course', 'error')
        return redirect(url_for('courses.detail', course_id=course_id))

@courses_bp.route('/api-test')
def test_api():
    """Test endpoint to check API responses"""
    try:
        # Import OpenEdxAPI only when needed
        api = OpenEdxAPI()
        headers = api._get_auth_headers()
        
        # Test course modes API
        modes_url = f"{api.base_url}/api/enrollment/v1/course/modes"
        modes_response = api.session.get(
            modes_url,
            headers=headers,
            timeout=10
        )
        
        modes_data = {
            'status_code': modes_response.status_code,
            'headers': dict(modes_response.headers),
            'response': modes_response.json() if modes_response.status_code == 200 else modes_response.text
        }
        
        # Test course catalog API
        catalog_url = f"{api.base_url}/api/courses/v1/courses/"
        catalog_response = api.session.get(
            catalog_url,
            headers=headers,
            timeout=10
        )
        
        catalog_data = {
            'status_code': catalog_response.status_code,
            'headers': dict(catalog_response.headers),
            'response': catalog_response.json() if catalog_response.status_code == 200 else catalog_response.text
        }
        
        # Test commerce API for a specific course
        test_course_id = "course-v1:OpenedX+DemoX+DemoCourse"
        commerce_url = f"{api.base_url}/api/commerce/v1/courses/{test_course_id}/"
        commerce_response = api.session.get(
            commerce_url,
            headers=headers,
            timeout=10
        )
        
        commerce_data = {
            'status_code': commerce_response.status_code,
            'headers': dict(commerce_response.headers),
            'response': commerce_response.json() if commerce_response.status_code == 200 else commerce_response.text
        }
        
        return jsonify({
            'config': {
                'base_url': api.base_url,
                'client_id_set': bool(api.client_id),
                'client_secret_set': bool(api.client_secret),
                'access_token': api.access_token,
                'csrf_token': api.csrf_token
            },
            'auth_headers': headers,
            'modes_api': modes_data,
            'catalog_api': catalog_data,
            'commerce_api': commerce_data
        })
        
    except Exception as e:
        logging.error(f"API test error: {str(e)}")
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@courses_bp.route('/api-info')
def test_api_info():
    """Test the OpenEdX instance info and available endpoints."""
    # Import OpenEdxAPI only when needed
    edx_api = OpenEdxAPI()
    results = {
        'config': {
            'base_url': edx_api.base_url,
            'verify_ssl': edx_api.verify_ssl,
            'client_id_set': bool(edx_api.client_id),
            'client_secret_set': bool(edx_api.client_secret)
        },
        'endpoints': {},
        'errors': []
    }
    
    # Test basic endpoints without auth
    endpoints = [
        '/',
        '/api',
        '/oauth2',
        '/api/oauth2',
        '/api/courses/v1',
        '/api/enrollment/v1',
        '/api/user/v1'
    ]
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'EDXStore/1.0'
    }
    
    for endpoint in endpoints:
        try:
            url = urljoin(edx_api.base_url, endpoint)
            response = requests.get(
                url,
                headers=headers,
                verify=edx_api.verify_ssl,
                allow_redirects=False
            )
            
            results['endpoints'][endpoint] = {
                'status_code': response.status_code,
                'headers': dict(response.headers)
            }
            
            # Try to get response content if JSON
            try:
                results['endpoints'][endpoint]['content'] = response.json()
            except:
                if len(response.text) < 1000:  # Only include text if it's not too long
                    results['endpoints'][endpoint]['text'] = response.text
                
        except Exception as e:
            results['errors'].append(f'Error checking {endpoint}: {str(e)}')
    
    return jsonify(results)

@courses_bp.route('/oauth2-test')
def test_oauth2():
    """Test the OAuth2 configuration and endpoints."""
    # Import OpenEdxAPI only when needed
    edx_api = OpenEdxAPI()
    results = {
        'config': {
            'base_url': edx_api.base_url,
            'verify_ssl': edx_api.verify_ssl,
            'client_id_set': bool(edx_api.client_id),
            'client_secret_set': bool(edx_api.client_secret)
        },
        'oauth2_endpoints': {},
        'errors': []
    }
    
    # Test OAuth2 endpoints
    oauth2_endpoints = [
        '/oauth2/access_token',
        '/oauth2/authorize',
        '/oauth2/user_info'
    ]
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'EDXStore/1.0'
    }
    
    # First test endpoints without auth
    for endpoint in oauth2_endpoints:
        try:
            url = urljoin(edx_api.base_url, endpoint)
            response = requests.get(
                url,
                headers=headers,
                verify=edx_api.verify_ssl,
                allow_redirects=False
            )
            
            results['oauth2_endpoints'][endpoint] = {
                'url': url,
                'status_code': response.status_code,
                'headers': dict(response.headers)
            }
            
            if len(response.text) < 1000:
                results['oauth2_endpoints'][endpoint]['response'] = response.text
            
        except Exception as e:
            results['errors'].append(f'Error checking {endpoint}: {str(e)}')
    
    # Now try to get a token
    try:
        token_url = urljoin(edx_api.base_url, 'oauth2/access_token')
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': edx_api.client_id,
            'client_secret': edx_api.client_secret
        }
        token_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'EDXStore/1.0'
        }
        
        response = requests.post(
            token_url,
            data=token_data,
            headers=token_headers,
            verify=edx_api.verify_ssl,
            allow_redirects=False
        )
        
        results['token_request'] = {
            'url': token_url,
            'status_code': response.status_code,
            'headers': dict(response.headers)
        }
        
        if len(response.text) < 1000:
            results['token_request']['response'] = response.text
            
    except Exception as e:
        results['errors'].append(f'Error making token request: {str(e)}')
    
    return jsonify(results)

@courses_bp.route('/courses-test')
def test_courses():
    """Test the course listing endpoint."""
    # Import OpenEdxAPI only when needed
    edx_api = OpenEdxAPI()
    results = {
        'config': {
            'base_url': edx_api.base_url,
            'verify_ssl': edx_api.verify_ssl,
            'client_id_set': bool(edx_api.client_id),
            'client_secret_set': bool(edx_api.client_secret)
        },
        'courses': None,
        'errors': []
    }
    
    try:
        # First get a token
        token = edx_api.get_access_token()
        results['token'] = {
            'obtained': bool(token),
            'value': token[:10] + '...' if token else None  # Only show first 10 chars
        }
        
        # Now try to get courses
        courses = edx_api.get_courses(page=1, page_size=5)
        results['courses'] = {
            'count': len(courses.get('results', [])),
            'sample': courses.get('results', [])[:2] if courses.get('results') else None,
            'pagination': courses.get('pagination')
        }
        
        # Test course modes for first course if available
        if courses.get('results'):
            first_course = courses['results'][0]
            course_id = first_course.get('id')
            if course_id:
                modes = edx_api.get_course_modes(course_id)
                results['sample_modes'] = {
                    'course_id': course_id,
                    'modes': modes
                }
        
    except Exception as e:
        import traceback
        results['errors'].append({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
    
    return jsonify(results)

@courses_bp.route('/courses-api-test')
def test_courses_api():
    """Test the courses API endpoints in detail."""
    # Import OpenEdxAPI only when needed
    edx_api = OpenEdxAPI()
    results = {
        'config': {
            'base_url': edx_api.base_url,
            'verify_ssl': edx_api.verify_ssl,
            'client_id_set': bool(edx_api.client_id),
            'client_secret_set': bool(edx_api.client_secret)
        },
        'api_tests': {},
        'errors': []
    }
    
    # First get a token
    try:
        token = edx_api.get_access_token()
        results['token'] = {
            'obtained': bool(token),
            'value': token[:10] + '...' if token else None
        }
        
        if token:
            # Test different API paths
            api_paths = [
                'api/courses/v1/courses/',
                'api/courses/v1/courses',
                'api/course/v1/courses/',
                'api/course/v1/courses',
                'api/courses/courses/',
                'courses/v1/courses/'
            ]
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            params = {
                'page': 1,
                'page_size': 1,
                'username': '',
                'org': '',
                'mobile': True
            }
            
            for api_path in api_paths:
                try:
                    url = urljoin(edx_api.base_url, api_path)
                    response = requests.get(
                        url,
                        headers=headers,
                        params=params,
                        verify=edx_api.verify_ssl,
                        allow_redirects=False
                    )
                    
                    results['api_tests'][api_path] = {
                        'url': url,
                        'status_code': response.status_code,
                        'headers': dict(response.headers)
                    }
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            results['api_tests'][api_path]['response'] = data
                        except:
                            if len(response.text) < 1000:
                                results['api_tests'][api_path]['raw_response'] = response.text
                    else:
                        if len(response.text) < 1000:
                            results['api_tests'][api_path]['error_response'] = response.text
                    
                except Exception as e:
                    results['api_tests'][api_path] = {
                        'url': url,
                        'error': str(e)
                    }
                    
            # Also test the catalog API if available
            catalog_paths = [
                'api/catalog/v1/catalogs/',
                'api/catalog/v1/courses/',
                'api/catalog/courses/'
            ]
            
            for catalog_path in catalog_paths:
                try:
                    url = urljoin(edx_api.base_url, catalog_path)
                    response = requests.get(
                        url,
                        headers=headers,
                        verify=edx_api.verify_ssl,
                        allow_redirects=False
                    )
                    
                    results['api_tests'][f'catalog_{catalog_path}'] = {
                        'url': url,
                        'status_code': response.status_code,
                        'headers': dict(response.headers)
                    }
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            results['api_tests'][f'catalog_{catalog_path}']['response'] = data
                        except:
                            if len(response.text) < 1000:
                                results['api_tests'][f'catalog_{catalog_path}']['raw_response'] = response.text
                    
                except Exception as e:
                    results['api_tests'][f'catalog_{catalog_path}'] = {
                        'url': url,
                        'error': str(e)
                    }
        
    except Exception as e:
        import traceback
        results['errors'].append({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
    
    return jsonify(results)

@courses_bp.route('/config-test')
def test_config():
    """Test the OpenEdX API configuration."""
    # Import OpenEdxAPI only when needed
    config = {
        'OPENEDX_URL': os.getenv('OPENEDX_URL'),
        'OPENEDX_CLIENT_ID': bool(os.getenv('OPENEDX_CLIENT_ID')),  # Don't expose actual value
        'OPENEDX_CLIENT_SECRET': bool(os.getenv('OPENEDX_CLIENT_SECRET')),  # Don't expose actual value
        'FLASK_DEBUG': os.getenv('FLASK_DEBUG'),
        'FLASK_ENV': os.getenv('FLASK_ENV')
    }
    
    edx_api = OpenEdxAPI()
    
    try:
        token = edx_api.get_access_token()
        config['token_obtained'] = bool(token)
        
        # Test courses endpoint
        courses_api_url = urljoin(edx_api.base_url, 'api/courses/v1/courses/')
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        response = requests.get(
            courses_api_url,
            headers=headers,
            verify=edx_api.verify_ssl
        )
        
        config['courses_api_status'] = response.status_code
        config['courses_api_response'] = response.text[:1000] if response.text else None
        
    except Exception as e:
        config['error'] = str(e)
    
    return jsonify(config)

@courses_bp.route('/api-raw')
def test_api_raw():
    """Test the raw API response."""
    # Import OpenEdxAPI only when needed
    edx_api = OpenEdxAPI()
    results = {
        'token': None,
        'courses_response': None,
        'error': None
    }
    
    try:
        # Get token
        token = edx_api.get_access_token()
        results['token'] = {
            'obtained': bool(token),
            'value': token[:10] + '...' if token else None
        }
        
        if token:
            # Test courses endpoint
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            # Make request to courses API
            courses_url = urljoin(edx_api.base_url, 'api/courses/v1/courses/')
            response = requests.get(
                courses_url,
                headers=headers,
                verify=edx_api.verify_ssl
            )
            
            results['courses_response'] = {
                'url': courses_url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text if response.text else None
            }
            
            # If we get a successful response, try to parse it
            if response.status_code == 200:
                try:
                    data = response.json()
                    results['parsed_data'] = data
                except Exception as e:
                    results['parse_error'] = str(e)
            
            # Also test course modes for a sample course
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('results') and len(data['results']) > 0:
                        course_id = data['results'][0]['id']
                        modes_url = urljoin(edx_api.base_url, f'api/course_modes/v1/courses/{course_id}/')
                        modes_response = requests.get(
                            modes_url,
                            headers=headers,
                            verify=edx_api.verify_ssl
                        )
                        results['modes_response'] = {
                            'url': modes_url,
                            'status_code': modes_response.status_code,
                            'headers': dict(modes_response.headers),
                            'content': modes_response.text if modes_response.text else None
                        }
                except Exception as e:
                    results['modes_error'] = str(e)
                    
    except Exception as e:
        results['error'] = str(e)
    
    return jsonify(results)

@courses_bp.route('/commerce-test')
def test_commerce_api():
    """Test endpoint for verifying commerce API functionality"""
    try:
        # Import OpenEdxAPI only when needed
        api = OpenEdxAPI()
        results = {
            'config': {
                'base_url': api.base_url,
                'verify_ssl': api.verify_ssl,
                'client_id_set': bool(api.client_id),
                'client_secret_set': bool(api.client_secret)
            },
            'tests': {}
        }
        
        # Test 1: Get CSRF token
        csrf_token = api._get_csrf_token()
        results['tests']['csrf_token'] = {
            'success': bool(csrf_token),
            'token': csrf_token
        }
        
        # Test 2: Get access token
        access_token = api._get_access_token()
        results['tests']['access_token'] = {
            'success': bool(access_token),
            'token': access_token[:10] + '...' if access_token else None
        }
        
        # Test 3: Try different course IDs with commerce API
        test_course_ids = [
            'course-v1:OpenedX+DemoX+DemoCourse',
            'course-v1:edX+DemoX+Demo_Course',
            'course-v1:ESLSCA+CS101+2024'
        ]
        
        results['tests']['commerce'] = []
        
        for course_id in test_course_ids:
            try:
                # Prepare headers
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'User-Agent': 'EDXStore/1.0',
                    'Referer': api.base_url,
                    'Origin': api.base_url
                }
                
                if csrf_token:
                    headers['X-CSRFToken'] = csrf_token
                    headers['Cookie'] = f'csrftoken={csrf_token}'
                
                if access_token:
                    headers['Authorization'] = f'Bearer {access_token}'
                
                # Try commerce API
                commerce_url = f"{api.base_url}/api/commerce/v1/courses/{course_id}/"
                commerce_response = requests.get(
                    commerce_url,
                    headers=headers,
                    verify=api.verify_ssl,
                    timeout=10,
                    allow_redirects=True
                )
                
                test_result = {
                    'course_id': course_id,
                    'commerce_api': {
                        'url': commerce_url,
                        'status_code': commerce_response.status_code,
                        'headers_sent': headers,
                        'headers_received': dict(commerce_response.headers)
                    }
                }
                
                # Add response based on content type
                content_type = commerce_response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    try:
                        test_result['commerce_api']['response'] = commerce_response.json()
                    except:
                        test_result['commerce_api']['response'] = commerce_response.text
                else:
                    test_result['commerce_api']['response'] = commerce_response.text
                
                # If commerce API fails, try course modes API
                if commerce_response.status_code != 200:
                    modes_url = f"{api.base_url}/api/enrollment/v1/course/{course_id}/modes"
                    modes_response = requests.get(
                        modes_url,
                        headers=headers,
                        verify=api.verify_ssl,
                        timeout=10,
                        allow_redirects=True
                    )
                    
                    test_result['modes_api'] = {
                        'url': modes_url,
                        'status_code': modes_response.status_code,
                        'headers_sent': headers,
                        'headers_received': dict(modes_response.headers)
                    }
                    
                    # Add response based on content type
                    content_type = modes_response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        try:
                            test_result['modes_api']['response'] = modes_response.json()
                        except:
                            test_result['modes_api']['response'] = modes_response.text
                    else:
                        test_result['modes_api']['response'] = modes_response.text
                
                results['tests']['commerce'].append(test_result)
                
            except Exception as e:
                results['tests']['commerce'].append({
                    'course_id': course_id,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500 

@courses_bp.route('/auth-test')
def test_auth():
    """Test endpoint to display authentication information"""
    try:
        # Import OpenEdxAPI only when needed
        api = OpenEdxAPI()
        
        # Get CSRF token
        csrf_token = api._get_csrf_token()
        
        # Get access token
        access_token = api._get_access_token()
        
        # Get auth headers
        headers = api._get_auth_headers()
        
        # Test a simple API call
        test_url = f"{api.base_url}/api/courses/v1/courses/"
        response = api.session.get(
            test_url,
            headers=headers,
            timeout=10
        )
        
        return jsonify({
            'config': {
                'base_url': api.base_url,
                'client_id_set': bool(api.client_id),
                'client_secret_set': bool(api.client_secret),
                'verify_ssl': api.verify_ssl
            },
            'auth': {
                'csrf_token': csrf_token,
                'access_token': access_token,
                'headers': headers
            },
            'test_request': {
                'url': test_url,
                'status_code': response.status_code,
                'headers_sent': dict(response.request.headers),
                'headers_received': dict(response.headers),
                'response': response.text[:500] if response.text else None
            }
        })
        
    except Exception as e:
        logging.error(f"Auth test error: {str(e)}")
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500 