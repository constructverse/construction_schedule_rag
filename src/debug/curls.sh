


# curl -X POST "http://localhost:8000/api/chat/get_activities" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "project_name": "output",
#     "user_report": "What concrete activities do I have?",
#     "top_k": 10
#   }'

# curl -X POST "http://localhost:8000/api/chat/get_summary" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "project_name": "output",
#     "user_text": "Can you summarize what events I have today?",
#     "top_k": 5
#   }'

curl -X POST "http://localhost:8000/api/chat/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "I want to know more about the foundation progress."
  }'