from rest_framework.throttling import UserRateThrottle


class SalesCreateThrottle(UserRateThrottle):
    scope = "sales_create"


class ReportsReadThrottle(UserRateThrottle):
    scope = "reports_read"


class ReportsWriteThrottle(UserRateThrottle):
    scope = "reports_write"


class AlertsScanThrottle(UserRateThrottle):
    scope = "alerts_scan"
