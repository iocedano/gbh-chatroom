## Overview
Build a real-time chat application with user authentication, multiple chat rooms, and message persistence. This challenge tests your ability to work with WebSockets, authentication, data modeling, and frontend-backend integration.

## Requirements

### Core features

1. **User authentication**
	- User registration with username and password
	- User login with JWT or session-based authentication
	- Protected routes/endpoints requiring authentication

2. **Chat rooms**
	- Create a new chat room
	- List available chat rooms
	- Join/leave chat rooms
	- Each room maintains its own message history

3. **Real-time messaging**
	- Send messages to a chat room
	- Receive messages in real-time (WebSocket or similar)
	- Display sender username and timestamp
	- **Typing indicator is optional**

4. **Data models**

```
User {
  id: string/number
  username: string (unique)
  passwordHash: string
  createdAt: datetime
}

ChatRoom {
  id: string/number
  name: string
  createdBy: User.id
  createdAt: datetime
}

Message {
  id: string/number
  content: string (max 1000 characters)
  roomId: ChatRoom.id
  senderId: User.id
  createdAt: datetime
}
```

### Technical requirements

- Backend: Any language/framework (Node.js, Python, Go, etc.)
- Real-time communication via WebSocket (or Socket.IO, Server-Sent Events)
- Data persistence (SQLite, PostgreSQL, MongoDB, or similar)
- Password hashing (bcrypt or similar)
- Input validation and sanitization
- **Frontend is optional.** A simple API-first implementation is acceptable.
	- If you do include a UI, keep it minimal and focus on correctness.

## Bonus points (Optional)

- Message read receipts or delivery status
- User online/offline status indicator
- Message search functionality
- Docker setup for easy deployment
- Rate limiting on message sending

## Deliverables

1. Source code in the repository as a pull request
2. README.md with:
	- Architecture overview
	- Setup and run instructions (including database setup)
	- Environment variables documentation
	- API documentation
3. Brief explanation of design decisions (can be in README)

## AI coding assistants

You are encouraged to use AI coding assistants (GitHub Copilot, ChatGPT, Claude, etc.) to help complete this challenge. However, be prepared to:
- Explain the WebSocket implementation and message flow
- Discuss authentication security considerations
- Walk through database schema design decisions
- Explain how you handle race conditions or concurrent users
- Modify or extend functionality during a follow-up discussion

**The goal is to demonstrate understanding, not just working code.**

## Tips for success

1. Start with authentication before real-time features
2. Get basic message sending working before adding typing indicators
3. Test with multiple browser windows to verify real-time functionality
4. Don't over-engineer the frontend functionality over aesthetics
5. Consider edge cases: What happens when a user disconnects?

Good luck!