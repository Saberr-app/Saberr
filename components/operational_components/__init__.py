from components import BaseComponent


class BaseOperationalComponent(BaseComponent):
    def __new__(cls, *args, **kwargs):
        if cls is BaseOperationalComponent:
            raise TypeError("BaseOperationalComponent is an abstract class and cannot be instantiated directly.")
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        from components.audit_log_component import AuditLogComponent
        super().__init__(*args, **kwargs)
        self._audit_log_component: AuditLogComponent = AuditLogComponent()
