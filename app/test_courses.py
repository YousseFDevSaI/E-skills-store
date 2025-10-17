import os
import requests
import json
import logging
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CourseAPI:
    def __init__(self):
        self.base_url = os.getenv('OPENEDX_URL', 'https://eskills.eslsca.edu.eg')
        self.client_id = os.getenv('OPENEDX_CLIENT_ID')
        self.client_secret = os.getenv('OPENEDX_CLIENT_SECRET')
        self.verify_ssl = False
        self.token = None
        
        # Log configuration
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Client ID set: {bool(self.client_id)}")
        logger.info(f"Client Secret set: {bool(self.client_secret)}")
        
    def get_token(self):
        """Get OAuth2 access token"""
        if not self.client_id or not self.client_secret:
            logger.error("Missing credentials - both client_id and client_secret are required")
            logger.error("Please check your .env file contains OPENEDX_CLIENT_ID and OPENEDX_CLIENT_SECRET")
            return None
            
        token_url = urljoin(self.base_url, 'oauth2/access_token')
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'token_type': 'jwt'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        try:
            logger.info(f"Requesting token from: {token_url}")
            logger.info(f"Using client_id: {self.client_id[:8]}..." if self.client_id else "No client_id set")
            
            response = requests.post(
                token_url,
                data=data,
                headers=headers,
                verify=self.verify_ssl
            )
            
            logger.info(f"Token response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get('access_token')
                logger.info("Successfully obtained access token")
                return self.token
            else:
                logger.error(f"Failed to get token. Status: {response.status_code}")
                logger.error(f"Error response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            return None

    def get_courses(self, page=1, page_size=20):
        """Get list of courses"""
        if not self.token:
            self.token = self.get_token()
            if not self.token:
                return {"error": "Could not obtain access token"}

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # List of endpoints to try
        endpoints = [
            'api/courses/v1/courses/',
            'api/courses/v1/courses',
            'api/course/v1/courses/',
            'api/course/v1/courses',
            'api/courses/courses/',
            'courses/v1/courses/',
            'api/v1/courses/',
            'api/v1/courses'
        ]
        
        params = {
            'page': page,
            'page_size': page_size,
            'username': '',
            'org': '',
            'mobile': True
        }
        
        for endpoint in endpoints:
            courses_api_url = urljoin(self.base_url, endpoint)
            logger.info(f"\nTrying endpoint: {courses_api_url}")
            logger.info(f"Request headers: {headers}")
            logger.info(f"Request params: {params}")
            
            try:
                response = requests.get(
                    courses_api_url,
                    headers=headers,
                    params=params,
                    verify=self.verify_ssl,
                    allow_redirects=True,
                    timeout=10
                )
                
                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    try:
                        courses_data = response.json()
                        if isinstance(courses_data, dict) and 'results' in courses_data:
                            logger.info(f"Successfully retrieved {len(courses_data.get('results', []))} courses")
                            return courses_data
                        else:
                            logger.warning(f"Unexpected response format from {endpoint}")
                    except ValueError as e:
                        logger.error(f"Failed to parse JSON response from {endpoint}: {e}")
                elif response.status_code == 401:
                    logger.warning("Token expired, attempting to get new token")
                    self.token = self.get_token()
                    if self.token:
                        headers['Authorization'] = f'Bearer {self.token}'
                        continue
                elif response.status_code == 404:
                    logger.warning(f"Endpoint {endpoint} not found")
                else:
                    logger.error(f"Request failed with status {response.status_code}")
                    if response.text:
                        logger.error(f"Response content: {response.text[:500]}...")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for {endpoint}: {str(e)}")
                continue
        
        logger.error("All endpoints failed")
        return {'results': [], 'pagination': {'count': 0, 'next': None, 'previous': None}}

def main():
    """Main function to test course fetching"""
    api = CourseAPI()
    
    # Check environment variables
    if not os.getenv('OPENEDX_CLIENT_ID') or not os.getenv('OPENEDX_CLIENT_SECRET'):
        logger.error("Environment variables not set!")
        logger.error("Please ensure your .env file contains:")
        logger.error("OPENEDX_CLIENT_ID=your_client_id")
        logger.error("OPENEDX_CLIENT_SECRET=your_client_secret")
        return
    
    # Get and print token
    token = api.get_token()
    if token:
        logger.info("Successfully obtained token")
        print("\nToken obtained successfully!")
    else:
        logger.error("Failed to obtain token")
        return
    
    # Get and print courses
    courses = api.get_courses()
    if isinstance(courses, dict) and courses.get('error'):
        logger.error(f"Error getting courses: {courses['error']}")
    else:
        print("\nCourses Response:")
        print(json.dumps(courses, indent=2))

if __name__ == '__main__':
    main() 