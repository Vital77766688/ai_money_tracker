# For web frameworks like FastAPI those classes might be inherited from HTTPException


class InstanceNotFound(Exception):
    ...


class ConstraintsViolation(Exception):
    ...


class FilterFieldNotAllowed(Exception):
    ...


class FilterOperationNotAllowed(Exception):
    ...
