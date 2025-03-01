# RAG for Schedule Update

## xml_parser.py (created by Yuna)

XML is converted into the readable json format. 
Json will have each activty with their attributs such as id, name, dates, predecessor, successor, and wbs.

## graph converter (created by Dou)
Given the json-formatted data, the schedule is converted into a graph-type data.

## RAG system

1. User questions or updates 
2. Similarity based search between a list of activities and user query. 
3. Retrieve top-k relevant schedule acitvitiy descriptions.
4. Extract the relevant a part of action graph.
5. Update the schedule attributes based on user query
