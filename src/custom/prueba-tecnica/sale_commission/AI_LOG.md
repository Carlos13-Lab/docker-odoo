# AI_LOG — sale_commission

Herramientas

    Claude Code (Claude, en la web de claude.ai/code).

Prompts clave

    Le pasé el PDF y le pedí un análisis completo para armar el repo.
        Me dio un plan por ejercicio; lo usé como guía, pero el repo de partida no estaba donde decía y tuve que encontrar la rama correcta.
    Le pedí encontrar la causa del ticket T-200.
        Leyó el commit 3f4d73f y encontró el permiso faltante y el uso de env.user. Yo lo confirmé con la prueba en rojo (AccessError) antes de corregir.
    Le pedí el INCIDENT.md.
        Me dio un borrador completo; lo revisé, comprobé el historial con git log y reescribí el mensaje al cliente.

Lo que la IA hizo mal

    Me dio una configuración de Postgres que no existía (postgresql.conf). Me di cuenta porque el contenedor quedaba en Restarting, y lo vi en los logs.
    Dijo que la base no se creaba por el límite de CPU; el error real, que vi en el traceback, era de permisos en el filestore.

Lo que escribí yo sin IA

    Corrí y verifiqué cada prueba en rojo y en verde en mi Docker.
    Decidí incluir en el hotfix el segundo error (la comisión del gerente), en un commit aparte.
