# Mini Forum

A small forum REST API built with Django REST Framework as a Developer Akademie assignment. Registered users write posts and comments, and token authentication with object-level permissions controls who can change them.

![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Django 5.2](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF 3.18](https://img.shields.io/badge/DRF-3.18-A30000)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?logo=uv&logoColor=white)

## Quickstart

**Prerequisites** — Git and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/kamycoding/mini-forum.git
cd mini-forum
uv venv --python 3.14
```

Activate the virtual environment on Linux or macOS:

```bash
source .venv/bin/activate
```

On Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies and create the local settings file:

```bash
uv pip sync requirements.txt
cp .env.example .env
```

Generate a secret key:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

In `.env`, paste it into `SECRET_KEY` inside single quotes and keep `DEBUG=True` for local development. Then run:

```bash
python manage.py migrate
```

Creating a superuser is optional for API-only use and required for the Django Admin demonstration.

```bash
python manage.py createsuperuser
```

Start the development server.

```bash
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/` and Django Admin at `http://127.0.0.1:8000/admin/`.

## Features

- User registration and token login
- Create, read, update and delete posts and comments
- Authors can change their own entries; admins (`is_staff`) can change any entry
- Management of posts and comments in Django Admin
- Automated API tests and a Bruno collection

## Tech stack

| Area | Tool |
| --- | --- |
| Language | Python 3.14 |
| Framework | Django 5.2, Django REST Framework 3.18 |
| Database | SQLite |
| Configuration | python-dotenv |
| Environment and packages | uv |

Dependency versions are pinned in `requirements.txt`.

## Project structure

```text
mini-forum/
├── core/               # Settings and root URLs
├── user_auth_app/
│   ├── api/            # Registration and login
│   └── tests.py
├── forum_app/
│   ├── api/            # Serializers, views, permissions and URLs
│   ├── migrations/
│   ├── admin.py
│   ├── models.py       # Post and Comment
│   └── tests.py
├── bruno/              # Bruno OpenCollection
├── .env.example
├── manage.py
└── requirements.txt
```

## API

### Endpoints

| Endpoint | Methods | Access |
| --- | --- | --- |
| `/auth/register/` | POST | Public |
| `/auth/login/` | POST | Public |
| `/api/posts/` | GET, POST | Authenticated |
| `/api/posts/{id}/` | GET, PUT, PATCH, DELETE | Read: authenticated. Write: author or admin |
| `/api/comments/` | GET, POST | Authenticated |
| `/api/comments/{id}/` | GET, PUT, PATCH, DELETE | Read: authenticated. Write: author or admin |

### Authentication

Register:

```json
{
  "username": "forum_reader",
  "email": "forum-reader@example.com",
  "password": "Harbor!Lantern-483",
  "repeated_password": "Harbor!Lantern-483"
}
```

The response contains `id`, `username` and `email`. Username and email must be unused.

Log in by sending `username` and `password` to `/auth/login/`. Send the returned token with every `/api/` request:

```http
Authorization: Token <token>
```

### Posts and comments

A post takes `title` (up to 200 characters) and `content`:

```json
{"title": "First discussion", "content": "Hello, forum."}
```

A comment takes the ID of an existing post and `text`:

```json
{"post": 1, "text": "Thanks for starting this discussion."}
```

- `id`, `author` and `created_at` are set by the server. Values sent by the client are ignored.
- A comment update may omit `post`. It cannot move the comment to another post.
- Deleting a post also deletes all of its comments, including those by other users.

### Status codes

| Status | Meaning |
| --- | --- |
| 200, 201, 204 | Read or updated, created, deleted |
| 400 | Invalid input or wrong login credentials |
| 401 | Missing or invalid token |
| 403 | Changing another user's entry without admin rights |
| 404 | Entry not found |

## Tests

Last verified locally on 27 November 2026: all 38 automated tests passed.
They cover authentication, validation, CRUD, ownership permissions, admin permissions, and model relationships.

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

### Bruno

1. In Bruno 4.3.0, choose **Open Collection** and select the `bruno/` folder. Select **Development** in the environment dropdown.
2. Copy the values needed for your local demo into `bruno/.env` using the variable names below. This file is ignored by Git. Set the collection variable `demo_suffix` when creating new accounts; to reuse existing users, skip registration.
3. Run **Accounts**, then **Forum**. Login tokens and created post/comment IDs are stored as runtime variables for subsequent requests. Run **Owner cleanup**, or log in as an admin and run **Admin cleanup**. Use the same Bruno session for the workflow.

`bruno/.env` supports `PASSWORD_USER_A`, `PASSWORD_USER_B`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `TOKEN_USER_A`, `TOKEN_USER_B`, `TOKEN_ADMIN`, `POST_ID`, and `COMMENT_ID`. Values can be left empty until needed; the login and creation requests populate runtime values. Never commit this file or real credentials.

## Notes and limitations

- Based on the [Mini Forum homework](https://hackmd.io/@mtUtNKDMTzWHLKW5U9RnOw/SkRKPkfMlg).
- The case-insensitive email uniqueness check applies to the registration endpoint only, not to Django Admin or direct database writes.
- Intended for local development. Tokens do not expire, and there is no rate limiting, pagination or email verification.
