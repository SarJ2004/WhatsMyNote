def response_formatter(state):
    if getattr(state, "error", None):
        return {"answer": f"Error: {state.error}"}

    if getattr(state, "saved_record_ids", None):
        count = len(state.saved_record_ids)
        return {"answer": f"Successfully created {count} record(s)."}

    if getattr(state, "updated_record_id", None):
        return {"answer": f"Record #{state.updated_record_id} updated successfully."}

    if getattr(state, "deleted_record_id", None):
        return {"answer": f"Record #{state.deleted_record_id} deleted successfully."}

    if getattr(state, "query_result", None) is not None:
        return {"answer": str(state.query_result)}

    return {"answer": "Operation completed."}
