from agents.router_agent import route_query

class MasterAgent:

    def process(self, query):

        route = route_query(query)

        return route