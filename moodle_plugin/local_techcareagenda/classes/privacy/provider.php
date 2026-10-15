<?php
// El plugin no guarda datos personales propios (la imagen vive en la etiqueta del curso).
namespace local_techcareagenda\privacy;

defined('MOODLE_INTERNAL') || die();

class provider implements \core_privacy\local\metadata\null_provider {
    public static function get_reason(): string {
        return 'privacy:metadata';
    }
}
