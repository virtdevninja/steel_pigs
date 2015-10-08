#   Copyright 2015 Michael Rice <michael@michaelrice.org>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from flask_wtf import Form
from wtforms.fields import *
from wtforms.validators import MacAddress, Regexp


class SearchByNameForm(Form):
    server_name = StringField(u'Server Name')
    submit = SubmitField(u'Get iPXE script')


class SearchByNumberForm(Form):
    server_number = IntegerField(u'Server Number', validators=[
        Regexp(
            regex="\d+",
            message="Only valid numbers are allowed"
        )
    ])
    submit = SubmitField(u'Get iPXE script')


class SearchByMacForm(Form):
    server_mac = StringField(u'Server MAC address', validators=[MacAddress(
        message="Must use a valid MAC address."
    )])
    submit = SubmitField(u'Get iPXE script')

