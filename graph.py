from nodes.intent_classifier import intent_evaluator, intent_router
from nodes.extractors.create_record_extractor import create_record_extractor
from nodes.extractors.update_record_extractor import update_record_extractor
from nodes.extractors.delete_record_extractor import delete_record_extractor
from langgraph.graph import START, StateGraph, END
from models.state import State
from nodes.writers.record_saver import record_saver
from nodes.writers.record_updater import record_updater
from nodes.writers.record_deleter import record_deleter

graph = StateGraph(State)

# Add nodes to the graph

graph.add_node("intent_evaluator", intent_evaluator)
graph.add_node(
    "create_record_extractor",
    create_record_extractor,
)

graph.add_node(
    "update_record_extractor",
    update_record_extractor,
)

graph.add_node(
    "delete_record_extractor",
    delete_record_extractor,
)

graph.add_node("record_saver", record_saver)
graph.add_node(
    "record_updater",
    record_updater,
)
graph.add_node(
    "record_deleter",
    record_deleter,
)

graph.add_edge(START, "intent_evaluator")
graph.add_conditional_edges(
    "intent_evaluator",
    intent_router,
    {
        "create_record_extractor": "create_record_extractor",
        "update_record_extractor": "update_record_extractor",
        "delete_record_extractor": "delete_record_extractor",
        "END": END,
    },
)
graph.add_edge("create_record_extractor", "record_saver")
graph.add_edge("update_record_extractor", "record_updater")
graph.add_edge("delete_record_extractor", "record_deleter")
graph.add_edge("record_saver", END)
graph.add_edge("record_updater", END)
graph.add_edge("record_deleter", END)

compiled_graph = graph.compile()
message = input("Enter your message: ")
result = compiled_graph.invoke({"raw_text": message})

if "saved_record_ids" in result:
    print(result["saved_record_ids"])

if "updated_record_id" in result:
    print("record updated id: ", result["updated_record_id"])
