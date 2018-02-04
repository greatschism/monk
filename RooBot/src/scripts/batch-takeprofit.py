# -*- coding: utf-8 -*-

#Reviewed by AJV 01/23/2018

from users import users
INIS = users.INI

from . import takeprofit
for ini in INIS.split():
    takeprofit.main(ini)
