import requests
from flask import current_app
import logging
import json
import traceback


logger = logging.getLogger(__name__)

class OpenEdxAPI:
    def __init__(self):
        """Initialize OpenEdxAPI with configuration from Flask app"""
        try:
            self.base_url = current_app.config['OPENEDX_URL'].rstrip('/')
            self.client_id = current_app.config['OPENEDX_CLIENT_ID']
            self.client_secret = current_app.config['OPENEDX_CLIENT_SECRET']
            self.access_token = ''  # Hardcoded token
            self.csrf_token = None
            self.verify_ssl = False
            self.session = requests.Session()
            self.session.verify = self.verify_ssl
            
            logger.info(f"Initialized OpenEdxAPI with base_url: {self.base_url}")
            logger.info(f"Client ID set: {bool(self.client_id)}")
            logger.info(f"Client Secret set: {bool(self.client_secret)}")
            
        except Exception as e:
            logger.error(f"Error initializing OpenEdxAPI: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _get_access_token(self):
        """Get OAuth2 access token from OpenEdX"""
        if not self.access_token:
            try:
                token_url = f"{self.base_url}/oauth2/access_token/"
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
                data = {
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'token_type': 'jwt'
                }

                logger.info(f"Requesting access token from {token_url}")
                response = self.session.post(
                    token_url,
                    headers=headers,
                    data=data,
                    timeout=10
                )
                
                logger.info(f"Token request status: {response.status_code}")
                logger.info(f"Token response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data.get('access_token')
                    if not self.access_token:
                        logger.error("Access token not found in response")
                    else:
                        logger.info("Successfully obtained access token")
                else:
                    logger.error(f"Token request failed: {response.text}, {self.client_id}, {self.client_secret}")
                    
            except Exception as e:
                logger.error(f"Error getting access token: {str(e)}")
                return None
        return self.access_token

    def _get_csrf_token(self):
        """Get CSRF token from OpenEdX"""
        if not self.csrf_token:
            try:
                logger.info("Requesting CSRF token")
                response = self.session.get(
                    self.base_url,
                    headers={'Accept': 'application/json'},
                    timeout=10
                )
                
                # Try to get CSRF token from cookies
                self.csrf_token = response.cookies.get('csrftoken')
                
                if not self.csrf_token:
                    # Try to get from response headers
                    self.csrf_token = response.headers.get('X-CSRFToken')
                
                if self.csrf_token:
                    logger.info("Successfully obtained CSRF token")
                else:
                    logger.warning("No CSRF token found in response")
                
            except Exception as e:
                logger.error(f"Error getting CSRF token: {str(e)}")
        return self.csrf_token

    def _get_auth_headers(self, include_csrf=True):
        """Get authentication headers for API requests"""
        logger.info(f"Getting authentication headers : {self._get_access_token()}")
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'EDXStore/1.0',
            'Authorization': f'jwt {self._get_access_token()}'
        }
        
        # Add CSRF token if requested
        if include_csrf:
            csrf = self._get_csrf_token()
            if csrf:
                headers['X-CSRFToken'] = csrf
                headers['Cookie'] = f'csrftoken={csrf}'
                
        return headers

    def get_courses(self, page=1, page_size=12):
        """Get list of available courses"""
        try:
            # Get courses from catalog API
            catalog_url = f"{self.base_url}/api/courses/v1/courses/"
            params = {
                'page': page,
                'page_size': page_size
            }
            
            headers = self._get_auth_headers()
            logger.info(f"Fetching courses from {catalog_url} with params: {params}")
            logger.info(f"Using headers: {headers}")
            
            response = self.session.get(
                catalog_url,
                headers=headers,
                params=params,
                timeout=10
            )
            
            logger.info(f"Courses API response status: {response.status_code}")
            logger.info(f"Courses API response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                courses = data.get('results', [])
                
                logger.info(f"Successfully fetched {len(courses)} courses")
                
                # Get price information for each course
                for course in courses:
                    course_id = course.get('id')
                    if course_id:
                        # Get price information from commerce API
                        commerce_url = f"{self.base_url}/api/commerce/v1/courses/{course_id}/"
                        logger.info(f"Fetching price information for course {course_id}")
                        commerce_response = self.session.get(
                            commerce_url,
                            headers=headers,
                            timeout=10
                        )
                        
                        if commerce_response.status_code == 200:
                            commerce_data = commerce_response.json()
                            # Look for professional or verified mode
                            for mode in commerce_data.get('modes', []):
                                if mode.get('name') in ['professional', 'verified']:
                                    price = float(mode.get('price', 0))
                                    course.update({
                                        'price': price,
                                        'currency': mode.get('currency', 'USD').upper(),
                                        'source': 'commerce_api'
                                    })
                                    logger.info(f"Found price {price} {course['currency']} for course {course_id}")
                                    break
                            # If no professional/verified mode, use the first mode with a price
                            if 'price' not in course:
                                for mode in commerce_data.get('modes', []):
                                    price = float(mode.get('price', 0))
                                    if price > 0:
                                        course.update({
                                            'price': price,
                                            'currency': mode.get('currency', 'USD').upper(),
                                            'source': 'commerce_api'
                                        })
                                        logger.info(f"Found price {price} {course['currency']} for course {course_id}")
                                        break
                        else:
                            logger.warning(f"Failed to get price for course {course_id}: {commerce_response.status_code}")
                        
                        # If commerce API failed or no price found, try course modes API
                        if 'price' not in course:
                            modes_url = f"{self.base_url}/api/enrollment/v1/course/{course_id}/modes"
                            logger.info(f"Trying course modes API for course {course_id}")
                            modes_response = self.session.get(
                                modes_url,
                                headers=headers,
                                timeout=10
                            )
                            
                            if modes_response.status_code == 200:
                                modes_data = modes_response.json()
                                # Look for professional or verified mode
                                for mode in modes_data:
                                    if mode.get('name') in ['professional', 'verified']:
                                        price = float(mode.get('price', 0))
                                        course.update({
                                            'price': price,
                                            'currency': mode.get('currency', 'USD').upper(),
                                            'source': 'course_modes_api'
                                        })
                                        logger.info(f"Found price {price} {course['currency']} for course {course_id}")
                                        break
                                # If no professional/verified mode, use the first mode with a price
                                if 'price' not in course:
                                    for mode in modes_data:
                                        price = float(mode.get('price', 0))
                                        if price > 0:
                                            course.update({
                                                'price': price,
                                                'currency': mode.get('currency', 'USD').upper(),
                                                'source': 'course_modes_api'
                                            })
                                            logger.info(f"Found price {price} {course['currency']} for course {course_id}")
                                            break
                            else:
                                logger.warning(f"Failed to get course modes for course {course_id}: {modes_response.status_code}")
                
                return {
                    'results': courses,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total': data.get('count', 0)
                    }
                }
            else:
                logger.error(f"Failed to fetch courses: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching courses: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_course_details(self, course_id):
        """Get detailed information about a specific course"""
        try:
            # Try the new API endpoint
            api_url = f"{self.base_url}/api/courses/v1/courses/{course_id}"
            headers = self._get_auth_headers()
            
            logger.info(f"Fetching course details for {course_id} from {api_url}")
            logger.info(f"Using headers: {headers}")
            
            response = self.session.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                course = response.json()
                logger.info(f"Successfully fetched course details for {course_id}, course: {course}")
                
                # Get price information
                price_info = self.get_course_price(course_id)
                course.update(price_info)
                course_mode = self.get_course_mode(course_id)
                # Ensure required fields are present
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
                    'mobile_available': course.get('mobile_available', True) , # Add mobile availability
                    'mode': course_mode.get('name', 'Not specified')
                })
                
                return course
                
            else:
                logger.warning(f"Failed to fetch course details from new API: {response.status_code}")
                logger.warning(f"Response content: {response.text}")
                
                # Try the legacy endpoint
                api_url = f"{self.base_url}/api/mobile/v0.5/course_info/{course_id}"
                logger.info(f"Trying legacy endpoint for course {course_id} at {api_url}")
                response = self.session.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    course = response.json()
                    logger.info(f"Successfully fetched course details from legacy endpoint for {course_id}")
                    
                    # Get price information
                    price_info = self.get_course_price(course_id)
                    course.update(price_info)
                    course_mode = self.get_course_mode(course_id)
                    
                    # Ensure required fields are present
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
                        'mobile_available': course.get('mobile_available', True) , # Add mobile availability
                        'mode': course_mode.get('name', 'Not specified')
                    })
                    
                    return course
                else:
                    logger.error(f"Failed to fetch course details from legacy API: {response.status_code}")
                    logger.error(f"Response content: {response.text}")
                    return None
                
        except Exception as e:
            logger.error(f"Error fetching course details: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def create_user(self, username, email, password, name=None, country=None, level_of_education=None, gender=None, honor_code=False, marketing_emails_opt_in=True):
        """Create a new user in OpenEDX LMS using the users API endpoint"""
        try:
            # Use the users API endpoint
            api_url = f"{self.base_url}/api/user/v1/account/registration/"
            
            # Format username - remove spaces and special characters
            username = ''.join(c for c in username if c.isalnum() or c in '._').lower()
            
            # Format name if not provided
            if not name:
                name = username.replace('.', ' ').replace('_', ' ').title()
            
            # Ensure name is properly formatted
            name = name.strip()
            if not name:
                name = username.title()
                
            # Data structure for user creation
            data = {
                'username': username,
                'email': email.strip(),
                'password': password,
                'name': name,
                'country': country or 'EG',  # Default to US if not provided
                'gender': gender or 'o',  # Default to 'other' if not provided
                'level_of_education': level_of_education or 'none',  # Default to 'none' if not provided
                'goals': 'Learn new skills',
                'honor_code': honor_code,
                'terms_of_service': honor_code,
                'language': 'en',
                'year_of_birth': '1990',
                'marketing_emails_opt_in': marketing_emails_opt_in
            }
            
            # Log the request data for debugging
            logger.info(f"Attempting to create user with data in api url {api_url}: {data}")
            
            # Get CSRF token
            csrf_response = self.session.get(self.base_url)
            csrf_token = csrf_response.cookies.get('csrftoken')
            
            headers = {
                'Accept': 'application/json',
                'X-CSRFToken': csrf_token,
                'Cookie': f'csrftoken={csrf_token}',
                'Authorization': f'jwt {self._get_access_token()}'
            }
            
            # Send the request as form data
            response = self.session.post(api_url, headers=headers, data=data, verify=False)
            
            # Log the response for debugging
            logger.info(f"Registration response status: {response.status_code}")
            logger.info(f"Registration response headers: {dict(response.headers)}")
            logger.info(f"Registration response body: {response.text}")
            
            if response.status_code in [200, 201]:
                user_data = response.json()
                logger.info(f"Successfully created user {username} in OpenEDX, user data: {user_data}")
                return user_data, None, username
            else:
                error_data = response.json() if response.text else {}
                error_messages = []
                
                # Extract user-friendly error messages
                for field, errors in error_data.items():
                    if isinstance(errors, list):
                        for error in errors:
                            if isinstance(error, dict) and 'user_message' in error:
                                error_messages.append(f"{field}: {error['user_message']}")
                            else:
                                error_messages.append(f"{field}: {error}")
                
                error_str = '; '.join(error_messages) if error_messages else response.text
                logger.error(f"Failed to create user in OpenEDX. Status: {response.status_code}, Errors: {error_str}")
                return None, error_str, None
                
        except Exception as e:
            logger.error(f"Error creating user in OpenEDX: {str(e)}")
            return None
    
    def get_user_enrollments(self, username):
        """Get all enrollments for a user"""
        try:
            api_url = f"{self.base_url}/api/enrollment/v1/enrollment"
            headers = {
                'Authorization': f'jwt {self._get_access_token()}'
            }
            params = {'user': username}
            
            logger.info(f"Fetching enrollments for user {username}")
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            logger.info(f"Successfully fetched enrollments for user {username}")
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching user enrollments: {str(e)}")
            return []

    def get_course_price(self, course_id):
        """Get price information for a course"""
        try:
            # Try commerce API first
            commerce_url = f"{self.base_url}/api/commerce/v1/courses/{course_id}/"
            logger.info(f"Fetching price information from commerce API for course {course_id}")
            commerce_response = self.session.get(
                commerce_url,
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if commerce_response.status_code == 200:
                commerce_data = commerce_response.json()
                # Look for professional or verified mode
                for mode in commerce_data.get('modes', []):
                    if mode.get('name') in ['professional', 'verified']:
                        price = float(mode.get('price', 0))
                        return {
                            'price': price,
                            'currency': mode.get('currency', 'USD').upper(),
                            'source': 'commerce_api'
                        }
                # If no professional/verified mode, use the first mode with a price
                for mode in commerce_data.get('modes', []):
                    price = float(mode.get('price', 0))
                    if price > 0:
                        return {
                            'price': price,
                            'currency': mode.get('currency', 'USD').upper(),
                            'source': 'commerce_api'
                        }
            
            # If commerce API failed or no price found, try course modes API
            modes_url = f"{self.base_url}/api/enrollment/v1/course/{course_id}/modes"
            logger.info(f"Trying course modes API for course {course_id}")
            modes_response = self.session.get(
                modes_url,
                headers=self._get_auth_headers(),
                timeout=10
            )
            
            if modes_response.status_code == 200:
                modes_data = modes_response.json()
                # Look for professional or verified mode
                for mode in modes_data:
                    if mode.get('name') in ['professional', 'verified']:
                        price = float(mode.get('price', 0))
                        return {
                            'price': price,
                            'currency': mode.get('currency', 'USD').upper(),
                            'source': 'course_modes_api'
                        }
                # If no professional/verified mode, use the first mode with a price
                for mode in modes_data:
                    price = float(mode.get('price', 0))
                    if price > 0:
                        return {
                            'price': price,
                            'currency': mode.get('currency', 'USD').upper(),
                            'source': 'course_modes_api'
                        }
            
            # If no price found, return default values
            return {
                'price': 0,
                'currency': 'USD',
                'source': 'default'
            }
            
        except Exception as e:
            logger.error(f"Error getting course price: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'price': 0,
                'currency': 'USD',
                'source': 'error'
            }

    def get_course(self, course_id):
        """Get detailed information about a specific course"""
        try:
            # Get course details from catalog API
            catalog_url = f"{self.base_url}/api/courses/v1/courses/{course_id}/"
            logger.info(f"Fetching course details from {catalog_url}")
            
            headers = self._get_auth_headers()
            logger.info(f"Using headers: {headers}")
            
            response = self.session.get(
                catalog_url,
                headers=headers,
                timeout=10
            )
            
            logger.info(f"Course API response status: {response.status_code}")
            logger.info(f"Course API response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                course = response.json()
                logger.info(f"Successfully fetched course details for {course_id}")
                
                # Get price information from commerce API
                commerce_url = f"{self.base_url}/api/commerce/v1/courses/{course_id}/"
                logger.info(f"Fetching price information for course {course_id}")
                commerce_response = self.session.get(
                    commerce_url,
                    headers=headers,
                    timeout=10
                )
                
                if commerce_response.status_code == 200:
                    commerce_data = commerce_response.json()
                    # Look for professional or verified mode
                    for mode in commerce_data.get('modes', []):
                        if mode.get('name') in ['professional', 'verified']:
                            price = float(mode.get('price', 0))
                            course.update({
                                'price': price,
                                'currency': mode.get('currency', 'USD').upper(),
                                'source': 'commerce_api'
                            })
                            logger.info(f"Found price {price} {course['currency']} for course {course_id}")
                            break
                    # If no professional/verified mode, use the first mode with a price
                    if 'price' not in course:
                        for mode in commerce_data.get('modes', []):
                            price = float(mode.get('price', 0))
                            if price > 0:
                                course.update({
                                    'price': price,
                                    'currency': mode.get('currency', 'USD').upper(),
                                    'source': 'commerce_api'
                                })
                                logger.info(f"Found price {price} {course['currency']} for course {course_id}")
                                break
                else:
                    logger.warning(f"Failed to get price from commerce API for course {course_id}: {commerce_response.status_code}")
                
                # If commerce API failed or no price found, try course modes API
                if 'price' not in course:
                    modes_url = f"{self.base_url}/api/enrollment/v1/course/{course_id}/modes"
                    logger.info(f"Trying course modes API for course {course_id}")
                    modes_response = self.session.get(
                        modes_url,
                        headers=headers,
                        timeout=10
                    )
                    
                    if modes_response.status_code == 200:
                        modes_data = modes_response.json()
                        # Look for professional or verified mode
                        for mode in modes_data:
                            if mode.get('name') in ['professional', 'verified']:
                                price = float(mode.get('price', 0))
                                course.update({
                                    'price': price,
                                    'currency': mode.get('currency', 'USD').upper(),
                                    'source': 'course_modes_api'
                                })
                                logger.info(f"Found price {price} {course['currency']} for course {course_id}")
                                break
                        # If no professional/verified mode, use the first mode with a price
                        if 'price' not in course:
                            for mode in modes_data:
                                price = float(mode.get('price', 0))
                                if price > 0:
                                    course.update({
                                        'price': price,
                                        'currency': mode.get('currency', 'USD').upper(),
                                        'source': 'course_modes_api'
                                    })
                                    logger.info(f"Found price {price} {course['currency']} for course {course_id}")
                                    break
                
                # Set default price to 0 if no price found
                if 'price' not in course:
                    course.update({
                        'price': 0,
                        'currency': 'USD',
                        'source': 'default'
                    })
                    logger.info(f"No price found for course {course_id}, setting to 0")
                
                return course
            else:
                logger.error(f"Failed to fetch course details: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting course details: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def authenticate_user(self, username, password):
        """Authenticate a user with OpenEDX LMS"""
        try:
            api_url = f"{self.base_url}/oauth2/access_token"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            data = {
                'grant_type': 'password',
                'username': username,
                'password': password,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'read write'
            }
            
            logger.info(f"Attempting to authenticate user {username}")
            response = self.session.post(api_url, headers=headers, data=data, verify=False)
            
            if response.status_code == 200:
                token_data = response.json()
                logger.info(f"Successfully authenticated user {username}")
                return token_data
            else:
                logger.error(f"Failed to authenticate user. Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error authenticating user with OpenEDX: {str(e)}")
            return None

    def enroll(self, email, course_id, mode='audit'):
        """Enroll a user in a course using their email address"""
        try:
            # Get access token for authentication
            access_token = self._get_access_token()
            if not access_token:
                logger.error("Failed to get access token for enrollment")
                return False, "Authentication failed"
            # Prepare enrollment data
            enrollment_data = {
                'user': email,
                'course_details': {
                    'course_id': course_id,
                    
                },
                'mode': mode
            }

            # Get CSRF token
            csrf_token = self._get_csrf_token()
            if not csrf_token:
                logger.warning("No CSRF token available for enrollment")

            # Prepare headers
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': f'jwt {access_token}'
            }
            if csrf_token:
                headers['X-CSRFToken'] = csrf_token
                headers['Cookie'] = f'csrftoken={csrf_token}'

            # Make enrollment request
            enrollment_url = f"{self.base_url}/api/enrollment/v1/enrollment"
            logger.info(f"Attempting to enroll user {email} in course {course_id}")
            logger.info(f"Enrollment data: {enrollment_data['course_details']}")
            response = self.session.post(
                enrollment_url,
                headers=headers,
                json=enrollment_data,
                timeout=10
            )

            # Log response details
            logger.info(f"Enrollment response status: {response.status_code}")
            logger.info(f"Enrollment response body: {response.text}")

            if response.status_code in [200, 201]:
                enrollment_data = response.json()
                logger.info(f"Successfully enrolled user {email} in course {course_id}")
                return True, enrollment_data
            else:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('message', 'Unknown error occurred')
                logger.error(f"Failed to enroll user. Status: {response.status_code}, Error: {error_message}")
                return False, error_message

        except Exception as e:
            logger.error(f"Error enrolling user in course: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, str(e) 
        
    def get_course_mode(self, course_id):
        """Get the mode of a course"""
        try:
            # Format course ID if needed
            if not course_id.startswith('course-v1:'):
                course_id = f'course-v1:{course_id}'
                
            # Get course modes from API
            api_url = f"{self.base_url}/api/course_modes/v1/courses/{course_id}/"
            headers = self._get_auth_headers()
            
            logger.info(f"Fetching course modes for {course_id}")
            response = self.session.get(
                api_url,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                modes_data = response.json()
                logger.info(f"Successfully fetched course modes for {course_id}, modes: {modes_data}")
                
                # Look for professional or verified mode first
                for mode in modes_data:
                    if mode.get('mode_slug') in ['professional', 'verified']:
                        return {
                            'name': mode.get('mode_slug'),
                            'price': float(mode.get('price', 0)),
                            'currency': mode.get('currency', 'USD').upper()
                        }
                
                # If no professional/verified mode, return the first mode with a price
                for mode in modes_data:
                    price = float(mode.get('price', 0))
                    if price > 0:
                        return {
                            'name': mode.get('name'),
                            'price': price,
                            'currency': mode.get('currency', 'USD').upper()
                        }
                
                # If no paid modes found, return audit mode
                return {
                    'name': 'audit',
                    'price': 0,
                    'currency': 'USD'
                }
            else:
                logger.warning(f"Failed to get course modes for {course_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting course mode: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
