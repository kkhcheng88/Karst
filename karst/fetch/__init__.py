"""Source adapters (來源適配器): edgar, defeatbeta, prices, broker.

Every adapter lands raw returns under ``<out>/<source>/`` with a sibling
``.meta.json`` shaped like ``karst/tests/fixtures``. Identity (ticker, CIK),
dates and paths always arrive as parameters; nothing here knows any company.
"""
