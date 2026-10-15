<?php
// TechCare · Agendas: publica la imagen de la agenda semanal en el curso (General) y la reemplaza cada semana.
defined('MOODLE_INTERNAL') || die();
$plugin->component = 'local_techcareagenda';
$plugin->version   = 2026101500;
$plugin->requires  = 2023042400;   // Moodle 4.2+ (usa core_external\external_api)
$plugin->maturity  = MATURITY_BETA;
$plugin->release   = '0.2 (seguridad reforzada)';
