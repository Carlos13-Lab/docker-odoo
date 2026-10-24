{
    "name": "Solicitudes de pago",
    "summary": "Solicitudes de pago a proveedores con flujo de aprobación",
    "description": "Solicitudes de pago con aprobación. Documentación en README.md.",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Carlos Díaz",
    "license": "LGPL-3",
    "depends": ["account", "mail"],
    "data": [
        "security/payment_request_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/payment_request_views.xml",
        "views/payment_request_menus.xml",
    ],
    "installable": True,
    "application": True,
}
