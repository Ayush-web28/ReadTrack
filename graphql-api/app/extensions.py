"""
extensions.py: an EXTENSION hooks into every GraphQL execution.

This one reports how many REST calls a query caused, in the standard
"extensions" part of the response:

    { "data": {...}, "extensions": { "restCalls": 3 } }

It makes the N+1 problem (and its fix) visible and measurable.
"""

from strawberry.extensions import SchemaExtension


class RestCallCounter(SchemaExtension):
    def get_results(self):
        # Called after execution; the returned dict is merged into response.extensions.
        rest = self.execution_context.context.rest
        return {"restCalls": rest.call_count}
