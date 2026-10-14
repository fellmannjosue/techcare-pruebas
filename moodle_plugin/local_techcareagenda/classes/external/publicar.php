<?php
// Publica la imagen de la agenda en la sección 0 (General) del curso, en UNA "Área de texto y medios"
// (label) marcada con idnumber 'techcare_agenda'. La primera vez la crea; las siguientes REEMPLAZA la imagen.
namespace local_techcareagenda\external;

defined('MOODLE_INTERNAL') || die();

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;

class publicar extends external_api {

    const IDNUMBER = 'techcare_agenda';

    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid'    => new external_value(PARAM_INT, 'ID del curso'),
            'filename'    => new external_value(PARAM_FILE, 'Nombre del archivo (png/jpg)'),
            'filecontent' => new external_value(PARAM_RAW, 'Imagen en base64'),
            'alttext'     => new external_value(PARAM_TEXT, 'Texto alternativo', VALUE_DEFAULT, 'Agenda semanal'),
        ]);
    }

    public static function execute(int $courseid, string $filename, string $filecontent, string $alttext = 'Agenda semanal'): array {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/course/lib.php');
        require_once($CFG->dirroot . '/course/modlib.php');

        $p = self::validate_parameters(self::execute_parameters(), compact('courseid', 'filename', 'filecontent', 'alttext'));
        $course = get_course($p['courseid']);
        $ctxcurso = \context_course::instance($course->id);
        self::validate_context($ctxcurso);
        require_capability('moodle/course:manageactivities', $ctxcurso);

        $ext = strtolower(pathinfo($p['filename'], PATHINFO_EXTENSION));
        if (!in_array($ext, ['png', 'jpg', 'jpeg'])) {
            throw new \invalid_parameter_exception('Solo se aceptan imágenes PNG o JPG.');
        }
        $bin = base64_decode($p['filecontent'], true);
        if ($bin === false || strlen($bin) < 100) {
            throw new \invalid_parameter_exception('La imagen no llegó bien (base64 inválido o vacío).');
        }
        if (strlen($bin) > 15 * 1024 * 1024) {
            throw new \invalid_parameter_exception('La imagen pesa más de 15 MB.');
        }

        $labelmod = $DB->get_field('modules', 'id', ['name' => 'label'], MUST_EXIST);
        $cm = $DB->get_record('course_modules', ['course' => $course->id, 'module' => $labelmod,
                                                 'idnumber' => self::IDNUMBER, 'deletioninprogress' => 0]);
        $creado = false;
        if (!$cm) {
            $info = (object)[
                'modulename' => 'label', 'module' => $labelmod, 'course' => $course->id, 'section' => 0,
                'visible' => 1, 'visibleoncoursepage' => 1, 'cmidnumber' => self::IDNUMBER,
                'name' => 'Agenda semanal',
                // create_module() exige 'introeditor' (formato del editor; itemid 0 = sin archivos en borrador)
                'introeditor' => ['text' => '<p>Agenda semanal</p>', 'format' => FORMAT_HTML, 'itemid' => 0],
            ];
            $info = create_module($info);
            $cm = $DB->get_record('course_modules', ['id' => $info->coursemodule], '*', MUST_EXIST);
            $creado = true;
        }

        $ctxmod = \context_module::instance($cm->id);
        $fs = get_file_storage();
        $fs->delete_area_files($ctxmod->id, 'mod_label', 'intro');   // REEMPLAZA: fuera la agenda anterior
        $nombre = clean_param($p['filename'], PARAM_FILE);
        $fs->create_file_from_string(['contextid' => $ctxmod->id, 'component' => 'mod_label', 'filearea' => 'intro',
                                      'itemid' => 0, 'filepath' => '/', 'filename' => $nombre], $bin);

        $html = '<p><img src="@@PLUGINFILE@@/' . rawurlencode($nombre) . '" alt="' . s($p['alttext']) .
                '" class="img-fluid" style="max-width:100%;height:auto"></p>';
        $DB->update_record('label', (object)['id' => $cm->instance, 'intro' => $html, 'introformat' => FORMAT_HTML,
                                             'name' => 'Agenda semanal', 'timemodified' => time()]);
        rebuild_course_cache($course->id, true);

        return ['cmid' => (int)$cm->id, 'creado' => $creado,
                'url' => (new \moodle_url('/course/view.php', ['id' => $course->id]))->out(false)];
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid'   => new external_value(PARAM_INT, 'ID del módulo de la agenda'),
            'creado' => new external_value(PARAM_BOOL, 'true si se creó por primera vez; false si se reemplazó'),
            'url'    => new external_value(PARAM_URL, 'Enlace al curso'),
        ]);
    }
}
