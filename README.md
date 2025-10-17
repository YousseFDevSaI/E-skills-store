# EDX Store

A Flask-based storefront application for OpenEdX courses from eskills.eslsca.edu.eg.

## Features

- Browse available courses from OpenEdX
- View course details and descriptions
- User authentication and registration
- Course enrollment management
- Shopping cart functionality
- Integration with OpenEdX APIs

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following configuration:
```
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=your-secret-key
OPENEDX_URL=https://eskills.eslsca.edu.eg
OPENEDX_CLIENT_ID=your-client-id
OPENEDX_CLIENT_SECRET=your-client-secret
```

4. Run the application:
```bash
flask run
```

## Project Structure

```
edx_store/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   ├── routes/
│   ├── templates/
│   ├── static/
│   └── utils/
├── requirements.txt
└── README.md
```

## API Integration

This application integrates with the following OpenEdX APIs:
- Course Catalog API
- Enrollment API
- User API
- Commerce API

## Development

To contribute to this project:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License 