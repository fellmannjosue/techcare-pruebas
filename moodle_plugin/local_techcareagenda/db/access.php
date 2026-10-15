<?php
// Capacidad propia: NINGÚN rol la tiene por defecto. El administrador la asigna solo al usuario técnico de TechCare.
defined('MOODLE_INTERNAL') || die();

$capabilities = [
    'local/techcareagenda:publish' => [
        'riskbitmask'  => RISK_SPAM,
        'captype'      => 'write',
        'contextlevel' => CONTEXT_COURSE,
        'archetypes'   => [],
    ],
];
