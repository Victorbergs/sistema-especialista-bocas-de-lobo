# -*- coding: utf-8 -*-
"""Compatibilidade para executar Experta em versões novas do Python.

Equipe: <NOME DO INTEGRANTE 1>, <NOME DO INTEGRANTE 2>,
        <NOME DO INTEGRANTE 3>, <NOME DO INTEGRANTE 4>

Experta 1.9.4 depende de frozendict, que importa aliases removidos de
collections. Este módulo deve ser importado antes de qualquer módulo Experta.
"""

import collections
import collections.abc


# Restaura apenas os nomes que bibliotecas antigas esperam encontrar.
for _nome in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Callable"):
    if not hasattr(collections, _nome):
        setattr(collections, _nome, getattr(collections.abc, _nome))
