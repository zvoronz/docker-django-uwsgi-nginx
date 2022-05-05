# -*- coding: utf-8 -*-
#------------------------------------------------------------
# Name:        amsettings
# Author:      alexey.sychov@gameloft.com
# Created:     13/06/2016
# Description: Settings for G4 Tools project
#------------------------------------------------------------

from common_modules.models import Access


APPLICATIONS = (
    'Builds',
)

ADMINS = (
    'artem.drach@gameloft.com',
    'georgiy.voronov@gameloft.com',
    'valeria.lebed@gameloft.com',
    'konstantin.teslenko@gameloft.com',
    'ekaterina.yakusheva@gameloft.com',
)

# ------------------------------ init --------------------------------------- #

Access.init_applications(APPLICATIONS)
ACCESS_CONFIG = Access.get_access_config(APPLICATIONS)
get_access_config = lambda: Access.get_access_config(APPLICATIONS)
