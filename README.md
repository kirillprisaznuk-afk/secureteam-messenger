# SecureTeam Messenger

A Python desktop client-server messenger designed for internal team communication.

## Features

- PyQt5 desktop user interface
- TCP client-server communication
- JSON-over-TCP protocol with a 4-byte length header
- SQLite storage for users, chats, memberships, and messages
- Role-based access control (RBAC)
- User and chat management tools
- SHA-256 password hashing
- Multi-client server using Python threads
- Thread-safe database access

## Technologies

- Python
- PyQt5
- SQLite
- TCP sockets
- JSON
- Threading

## Project Structure

```text
client/     # Desktop interface and client-side networking
server/     # Server, authentication, database, and access control
shared/     # Protocol, constants, and shared models
```

## Running the Project

1. Clone the repository:

```bash
git clone https://github.com/kirillprisaznuk-afk/secureteam-messenger.git
cd secureteam-messenger
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
python run_server.py
```

4. Start the client in a separate terminal:

```bash
python run_client.py
```

## Security Note

This is an educational prototype. Passwords are hashed with SHA-256 before storage. A production system should use a salted adaptive password-hashing algorithm such as Argon2, bcrypt, or scrypt.
