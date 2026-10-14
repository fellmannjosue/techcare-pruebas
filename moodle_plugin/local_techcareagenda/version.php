<?php
// TechCare · Agendas: publica la imagen de la agenda semanal en el curso (General) y la reemplaza cada semana.
defined('MOODLE_INTERNAL') || die();
$plugin->component = 'local_techcareagenda';
$plugin->version   = 2026101401;
$plugin->requires  = 2023042400;   // Moodle 4.2+ (usa core_external\external_api)
$plugin->maturity  = MATURITY_ALPHA;
$plugin->release   = '0.1 (pruebas)';
