<?php
// TechCare · Agendas: publica la imagen de la agenda semanal en el curso (General) y la reemplaza cada semana.
defined('MOODLE_INTERNAL') || die();
$plugin->component = 'local_techcareagenda';
$plugin->version   = 2026102800;   // <--- 28-oct-2026: función listar + reemplazar una imagen existente de General
$plugin->requires  = 2023042400;   // Moodle 4.2+ (usa core_external\external_api)
$plugin->maturity  = MATURITY_BETA;
$plugin->release   = '0.3 (elegir y reemplazar lo que ya hay en General)';
