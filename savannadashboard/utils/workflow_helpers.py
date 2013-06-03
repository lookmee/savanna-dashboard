# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from horizon import forms
from horizon import workflows


class Parameter(object):
    def __init__(self, name, param_type, required=False, choices=None):
        self.name = name
        self.required = required
        self.param_type = param_type
        self.choices = choices


def build_control(parameter):
    if parameter.param_type == "text":
        return forms.CharField(
            label=parameter.name,
            required=parameter.required)

    elif parameter.param_type == "bool":
        return forms.BooleanField(
            label=parameter.name,
            required=False)

    elif parameter.param_type == "dropdown":
        return forms.ChoiceField(
            label=parameter.name,
            required=parameter.required,
            choices=parameter.choices)


def _create_step_action(name, title, parameters, advanced_fields=None):
    param_fields = {}
    contributes_field = ()
    meta_fields = []
    for param in parameters:
        field_name = name + "_" + param.name
        contributes_field += (field_name,)
        meta_fields.append(field_name)
        param_fields[field_name] = build_control(param)

    if advanced_fields is not None:
        for ad_field_name, ad_field_value in advanced_fields:
            param_fields[ad_field_name] = ad_field_value
            meta_fields.append(ad_field_name)

    action_meta = type('Meta', (object, ),
                       dict(name=title, fields=meta_fields))
    action = type(title,
                  (workflows.Action, action_meta),
                  param_fields)
    step_meta = type('Meta', (object,), dict(name=title))
    step = type(name,
                (workflows.Step, ),
                dict(name=name,
                     process_name=name,
                     action_class=action,
                     contributes=contributes_field,
                     Meta=step_meta))

    return step