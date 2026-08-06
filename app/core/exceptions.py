class OrderManagementException(Exception):
    """Base Exception"""
    pass


class CartNotFoundException(OrderManagementException):
    pass


class CartEmptyException(OrderManagementException):
    pass


class OrderNotFoundException(OrderManagementException):
    pass


class KOTNotFoundException(OrderManagementException):
    pass


class DuplicateKOTException(OrderManagementException):
    pass


class InvalidOrderStatusException(OrderManagementException):
    pass


class InvalidKOTStatusException(OrderManagementException):
    pass