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

from flask_wtf import FlaskForm
from wtforms.fields import IntegerField, StringField, SubmitField
from wtforms.validators import MacAddress, Regexp


class SearchByNameForm(FlaskForm):
    server_name = StringField("Server Name")
    submit = SubmitField("Get iPXE script")


class SearchByNumberForm(FlaskForm):
    server_number = IntegerField(
        "Server Number", validators=[Regexp(regex=r"\d+", message="Only valid numbers are allowed")]
    )
    submit = SubmitField("Get iPXE script")


class SearchByMacForm(FlaskForm):
    server_mac = StringField(
        "Server MAC address", validators=[MacAddress(message="Must use a valid MAC address.")]
    )
    submit = SubmitField("Get iPXE script")
