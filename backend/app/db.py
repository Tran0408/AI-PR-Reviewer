from prisma import Prisma

_prisma: Prisma | None = None


async def connect() -> Prisma:
    global _prisma
    if _prisma is None:
        _prisma = Prisma(auto_register=True)
    if not _prisma.is_connected():
        await _prisma.connect()
    return _prisma


async def disconnect() -> None:
    global _prisma
    if _prisma and _prisma.is_connected():
        await _prisma.disconnect()


def get_db() -> Prisma:
    if _prisma is None or not _prisma.is_connected():
        raise RuntimeError("Prisma not connected. Call connect() first.")
    return _prisma
