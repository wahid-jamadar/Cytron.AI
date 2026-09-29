import os
import sys

from tests.test_tech_stack_clarification import test_resolver_logic, test_analyze_stack_endpoint_incomplete, test_analyze_stack_endpoint_complete

if __name__ == "__main__":
    print("Running test_resolver_logic...")
    test_resolver_logic()
    print("Running test_analyze_stack_endpoint_incomplete...")
    test_analyze_stack_endpoint_incomplete()
    print("Running test_analyze_stack_endpoint_complete...")
    test_analyze_stack_endpoint_complete()
    print("All tests passed!")
