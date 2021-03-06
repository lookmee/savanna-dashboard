# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Red Hat Inc.
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

import json
import logging

from django.utils.translation import ugettext as _

from horizon import forms
from horizon import workflows

from savannadashboard.api.client import client as savannaclient
import savannadashboard.cluster_templates.workflows.create as t_flows
import savannadashboard.clusters.workflows.create as c_flow
import savannadashboard.utils.workflow_helpers as whelpers


LOG = logging.getLogger(__name__)


class SelectPluginAction(t_flows.SelectPluginAction):
    class Meta:
        name = _("Select plugin and hadoop version for cluster")
        help_text_template = ("clusters/_create_general_help.html")


class SelectPlugin(t_flows.SelectPlugin):
    pass


class JobExecutionGeneralConfigAction(workflows.Action):
    job_input = forms.ChoiceField(
        label=_("Input"),
        required=True,
        initial=(None, "None"),
        widget=forms.Select(attrs={"class": "job_input_choice"}))

    job_output = forms.ChoiceField(
        label=_("Output"),
        required=True,
        initial=(None, "None"),
        widget=forms.Select(attrs={"class": "job_output_choice"}))

    def __init__(self, request, *args, **kwargs):
        super(JobExecutionGeneralConfigAction, self). \
            __init__(request, *args, **kwargs)

        if request.REQUEST.get("job_id", None) is None:
            self.fields["job"] = forms.ChoiceField(
                label=_("Job"),
                required=True)
            self.fields["job"].choices = self.populate_job_choices(request)
        else:
            self.fields["job"] = forms.CharField(
                widget=forms.HiddenInput(),
                initial=request.REQUEST.get("job_id", None))

    def populate_job_input_choices(self, request, context):
        return self.get_data_source_choices(request, context)

    def populate_job_output_choices(self, request, context):
        return self.get_data_source_choices(request, context)

    def get_data_source_choices(self, request, context):
        savanna = savannaclient(request)
        data_sources = savanna.data_sources.list()

        choices = [(data_source.id, data_source.name)
                   for data_source in data_sources]

        return choices

    def populate_job_choices(self, request):
        savanna = savannaclient(request)
        jobs = savanna.jobs.list()

        choices = [(job.id, job.name)
                   for job in jobs]

        return choices

    class Meta:
        name = _("Job")
        help_text_template = \
            ("jobs/_launch_job_help.html")


class JobExecutionExistingGeneralConfigAction(JobExecutionGeneralConfigAction):
    cluster = forms.ChoiceField(
        label=_("Cluster"),
        required=True,
        initial=(None, "None"),
        widget=forms.Select(attrs={"class": "cluster_choice"}))

    def populate_cluster_choices(self, request, context):
        savanna = savannaclient(request)
        clusters = savanna.clusters.list()

        choices = [(cluster.id, cluster.name)
                   for cluster in clusters]

        return choices

    class Meta:
        name = _("Job")
        help_text_template = \
            ("jobs/_launch_job_help.html")


class JobConfigAction(workflows.Action):
    property_name = forms.ChoiceField(
        required=False,
    )

    job_configs = forms.CharField(
        required=False,
        widget=forms.HiddenInput())

    job_params = forms.CharField(
        required=False,
        widget=forms.HiddenInput())

    job_args = forms.CharField(
        required=False,
        widget=forms.HiddenInput())

    def __init__(self, request, *args, **kwargs):
        super(JobConfigAction, self).__init__(request, *args, **kwargs)

    def populate_property_name_choices(self, request, context):
        client = savannaclient(request)
        job_id = request.REQUEST.get("job_id") or request.REQUEST.get("job")
        job_type = client.jobs.get(job_id).type
        job_configs = client.jobs.get_configs(job_type).job_config
        choices = [(param['value'], param['name'])
                   for param in job_configs['configs']]
        return choices

    class Meta:
        name = _("Configure")
        help_text_template = \
            ("jobs/_launch_job_configure_help.html")


class JobExecutionGeneralConfig(workflows.Step):
    action_class = JobExecutionGeneralConfigAction

    def contribute(self, data, context):
        for k, v in data.items():
            context["job_general_" + k] = v

        return context


class JobExecutionExistingGeneralConfig(workflows.Step):
    action_class = JobExecutionExistingGeneralConfigAction

    def contribute(self, data, context):
        for k, v in data.items():
            context["job_general_" + k] = v

        return context


class JobConfig(workflows.Step):
    action_class = JobConfigAction
    template_name = 'jobs/config_template.html'

    def contribute(self, data, context):
        job_config = json.loads(data.get("job_configs", '{}'))
        job_params = json.loads(data.get("job_params", '{}'))
        job_args = json.loads(data.get("job_args", '{}'))
        context["job_config"] = {"configs": job_config,
                                 "params": job_params,
                                 "args": job_args}
        return context


class ClusterGeneralConfig(workflows.Step):
    action_class = c_flow.GeneralConfigAction
    contributes = ("hidden_configure_field", )

    def contribute(self, data, context):
        for k, v in data.items():
            context["cluster_general_" + k] = v

        return context


class LaunchJob(workflows.Workflow):
    slug = "launch_job"
    name = _("Launch Job")
    finalize_button_name = _("Launch")
    success_message = _("Job launched")
    failure_message = _("Could not launch job")
    success_url = "horizon:savanna:job_executions:index"
    default_steps = (JobExecutionExistingGeneralConfig, JobConfig)

    def handle(self, request, context):
        savanna = savannaclient(request)
        savanna.job_executions.create(
            context["job_general_job"],
            context["job_general_cluster"],
            context["job_general_job_input"],
            context["job_general_job_output"],
            context["job_config"])

        return True


class SelectHadoopPluginAction(t_flows.SelectPluginAction):
    def __init__(self, request, *args, **kwargs):
        super(SelectHadoopPluginAction, self).\
            __init__(request, *args, **kwargs)
        self.fields["job_id"] = forms.ChoiceField(
            label=_("Plugin name"),
            required=True,
            initial=request.GET["job_id"],
            widget=forms.HiddenInput(attrs={"class": "hidden_create_field"}))

    class Meta:
        name = _("Select plugin and hadoop version for cluster")
        help_text_template = ("cluster_templates/_create_general_help.html")


class SelectHadoopPlugin(workflows.Step):
    action_class = SelectHadoopPluginAction


class ChosePluginVersion(workflows.Workflow):
    slug = "lunch_job"
    name = _("Launch Job")
    finalize_button_name = _("Create")
    success_message = _("Created")
    failure_message = _("Could not create")
    success_url = "horizon:savanna:cluster_templates:index"
    default_steps = (SelectHadoopPlugin,)


class LaunchJobNewCluster(workflows.Workflow):
    slug = "launch_job"
    name = _("Launch Job")
    finalize_button_name = _("Launch")
    success_message = _("Job launched")
    failure_message = _("Could not launch job")
    success_url = "horizon:savanna:jobs:index"
    default_steps = (ClusterGeneralConfig,
                     JobExecutionGeneralConfig,
                     JobConfig)

    def handle(self, request, context):
        savanna = savannaclient(request)
        node_groups = None

        plugin, hadoop_version = whelpers. \
            get_plugin_and_hadoop_version(request)

        ct_id = context["cluster_general_cluster_template"] or None
        user_keypair = context["cluster_general_keypair"] or None

        cluster = savanna.clusters.create(
            context["cluster_general_cluster_name"],
            plugin, hadoop_version,
            cluster_template_id=ct_id,
            default_image_id=context["cluster_general_image"],
            description=context["cluster_general_description"],
            node_groups=node_groups,
            user_keypair_id=user_keypair,
            is_transient=True,
            net_id=context.get("cluster_general_neutron_management_network",
                               None))

        savanna.job_executions.create(
            context["job_general_job"],
            cluster.id,
            context["job_general_job_input"],
            context["job_general_job_output"],
            context["job_config"])

        return True
