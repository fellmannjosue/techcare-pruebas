<?php
defined('MOODLE_INTERNAL') || die();
$functions = [
    'local_techcareagenda_publicar' => [
        'classname'   => 'local_techcareagenda\external\publicar',
        'description' => 'Pone (o reemplaza) la imagen de la agenda semanal en la sección General del curso.',
        'type'        => 'write',
        'capabilities' => 'moodle/course:manageactivities',
    ],
];
$services = [
    'TechCare Agendas' => [
        'functions' => ['local_techcareagenda_publicar', 'core_webservice_get_site_info',
                        'core_course_get_courses_by_field', 'core_course_search_courses'],
        'restrictedusers' => 1,
        'enabled' => 1,
        'shortname' => 'techcare_agendas',
    ],
];
