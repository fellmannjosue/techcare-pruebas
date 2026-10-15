<?php
// Registro de auditoría: cada publicación de la agenda queda en Informes → Registros del curso.
namespace local_techcareagenda\event;

defined('MOODLE_INTERNAL') || die();

class agenda_publicada extends \core\event\base {

    protected function init() {
        $this->data['crud'] = 'u';
        $this->data['edulevel'] = self::LEVEL_OTHER;
        $this->data['objecttable'] = 'course_modules';
    }

    public static function get_name() {
        return get_string('eventagendapublicada', 'local_techcareagenda');
    }

    public function get_description() {
        $accion = !empty($this->other['creado']) ? 'creó' : 'reemplazó';
        return "El usuario con id '{$this->userid}' {$accion} la agenda semanal (módulo '{$this->objectid}') " .
               "del curso con id '{$this->courseid}' desde TechCare.";
    }

    public function get_url() {
        return new \moodle_url('/course/view.php', ['id' => $this->courseid]);
    }

    public static function get_objectid_mapping() {
        return ['db' => 'course_modules', 'restore' => 'course_module'];
    }

    public static function get_other_mapping() {
        return false;
    }
}
