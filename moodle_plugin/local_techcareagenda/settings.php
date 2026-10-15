<?php
// Administración del sitio → Plugins → Plugins locales → TechCare · Agendas.
defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $settings = new admin_settingpage('local_techcareagenda', get_string('pluginname', 'local_techcareagenda'));
    $settings->add(new admin_setting_configcheckbox('local_techcareagenda/enabled',
        get_string('enabled', 'local_techcareagenda'), get_string('enabled_desc', 'local_techcareagenda'), 0));
    $settings->add(new admin_setting_configtext('local_techcareagenda/allowedcategories',
        get_string('allowedcategories', 'local_techcareagenda'), get_string('allowedcategories_desc', 'local_techcareagenda'),
        '', PARAM_SEQUENCE));
    $ADMIN->add('localplugins', $settings);
}
