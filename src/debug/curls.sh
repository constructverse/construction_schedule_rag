# curl -X POST \
#      http://localhost:8000/api/chat/get_activities \
#      -H "Content-Type: application/json" \
#      -d '{
#          "project_name": "output",
#          "user_report": "I'\''m pouring concrete \"7 out of 10 parts\"",
#          "top_k": 3
#      }'


# curl -X POST \
#      http://localhost:8000/api/chat/update_activities \
#      -H "Content-Type: application/json" \
#      -d '{
#          "updates": [
#              {
#                  "object_id": "102564",
#                  "name": "Bid Package 3 - Building Concrete Package",
#                  "progress": 80.0
#              },
#              {
#                  "object_id": "102491",
#                  "name": "Demo Bituminous/Concrete Paving - Site Area 4",
#                  "progress": 90.0
#              }
#          ]
#      }'



# curl -X POST \
#      http://localhost:8000/api/chat/conversation \
#      -H "Content-Type: application/json" \
#      -d '{
#          "user_message": "Hello, how are you today?"
#      }'


curl -X POST \
     http://localhost:8000/api/chat/conversation \
     -H "Content-Type: application/json" \
     -d '{
         "session_id": "7b6c6265-f74a-477f-b1d4-288b5c6c1cf2",
         "user_message": "What are the steps to pouring concrete safely?"
     }'