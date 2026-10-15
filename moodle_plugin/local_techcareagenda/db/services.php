<?php
// Servicio restringido: solo los usuarios autorizados en el servicio pueden sacar token.
// Expone únicamente lo que TechCare usa (sin descarga ni subida de archivos genéricas).
defined('MOODLE_INTERNAL') || die();
$functions = [
    'local_techcareagenda_publicar' => [
        'classname'    => 'local_techcareagenda\external\publicar',
        'description'  => 'Pone (o reemplaza) la imagen de la agenda semanal en la sección General del curso.',
        'type'         => 'write',
        'capabilities' => 'local/techcareagenda:publish, moodle/course:manageactivities',
        'ajax'         => false,
    ],
];
$services = [
    'TechCare Agendas' => [
        'functions'       => ['local_techcareagenda_publicar', 'core_webservice_get_site_info',
                              'core_course_get_courses_by_field'],
        'restrictedusers' => 1,
        'enabled'         => 1,
        'downloadfiles'   => 0,
        'uploadfiles'     => 0,
        'shortname'       => 'techcare_agendas',
    ],
];
