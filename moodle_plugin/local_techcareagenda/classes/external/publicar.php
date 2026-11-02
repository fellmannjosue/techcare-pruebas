<?php
// Publica la imagen de la agenda en la sección 0 (General) del curso, en UNA "Área de texto y medios"
// (label) marcada con idnumber 'techcare_agenda'. La primera vez la crea; las siguientes REEMPLAZA la imagen.
//
// Seguridad (v0.2):
// - Interruptor general (apagado al instalar) y lista opcional de categorías permitidas (settings.php).
// - Capacidad propia local/techcareagenda:publish (ningún rol la tiene por defecto) + moodle/course:manageactivities.
// - La imagen se valida por su CONTENIDO (no por la extensión), con límites de peso y de píxeles, y se
//   RE-CODIFICA con GD: lo que se guarda es una imagen nueva, sin metadatos ni contenido oculto.
// - El nombre del archivo lo pone el plugin (nunca el que manda el cliente) y el texto alternativo se limpia.
// - Solo toca SU propia etiqueta (idnumber techcare_agenda); nunca otras actividades del curso.
// - Todo en una transacción y queda registrado en los registros de Moodle (evento agenda_publicada).
namespace local_techcareagenda\external;

defined('MOODLE_INTERNAL') || die();

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;

class publicar extends external_api {

    const IDNUMBER = 'techcare_agenda';
    const MAX_BYTES = 10 * 1024 * 1024;     // 10 MB de imagen ya decodificada
    const MAX_LADO = 8000;                  // px por lado
    const MAX_PIXELES = 25000000;           // 25 megapíxeles (evita "bombas" de descompresión)
    const MAX_ALT = 200;

    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid'    => new external_value(PARAM_INT, 'ID del curso'),
            'filename'    => new external_value(PARAM_FILE, 'Nombre original (solo informativo; el plugin pone el suyo)'),
            'filecontent' => new external_value(PARAM_RAW, 'Imagen PNG o JPG en base64'),
            'alttext'     => new external_value(PARAM_TEXT, 'Texto alternativo', VALUE_DEFAULT, 'Agenda semanal'),
            // <--- 28-oct-2026: si viene (>0), reemplaza esa actividad existente de General y la adopta como la agenda.
            'targetcmid'  => new external_value(PARAM_INT, 'cmid de la actividad a reemplazar (0 = la agenda de TechCare)',
                                                VALUE_DEFAULT, 0),
        ]);
    }

    public static function execute(int $courseid, string $filename, string $filecontent,
                                   string $alttext = 'Agenda semanal', int $targetcmid = 0): array {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/course/lib.php');
        require_once($CFG->dirroot . '/course/modlib.php');

        $p = self::validate_parameters(self::execute_parameters(),
            compact('courseid', 'filename', 'filecontent', 'alttext', 'targetcmid'));

        // 1) Interruptor general: el plugin no hace nada hasta que el administrador lo activa.
        if (!get_config('local_techcareagenda', 'enabled')) {
            throw new \moodle_exception('errordisabled', 'local_techcareagenda');
        }

        // 2) Curso real (nunca la portada del sitio), contexto y permisos.
        if ($p['courseid'] == SITEID) {
            throw new \moodle_exception('errorcourse', 'local_techcareagenda');
        }
        $course = get_course($p['courseid']);
        $ctxcurso = \context_course::instance($course->id);
        self::validate_context($ctxcurso);
        require_capability('local/techcareagenda:publish', $ctxcurso);
        require_capability('moodle/course:manageactivities', $ctxcurso);
        self::validar_categoria($course);

        // 3) Imagen: tamaño antes de decodificar, base64 estricto, tipo REAL por contenido y re-codificación.
        if (strlen($p['filecontent']) > (int)ceil(self::MAX_BYTES * 4 / 3) + 4) {
            throw new \moodle_exception('errortoobig', 'local_techcareagenda', '', self::MAX_BYTES / 1048576);
        }
        $bin = base64_decode($p['filecontent'], true);
        if ($bin === false || strlen($bin) < 100) {
            throw new \moodle_exception('errorbadimage', 'local_techcareagenda');
        }
        [$limpio, $ext] = self::recodificar($bin);
        unset($bin);

        $alt = trim(\core_text::substr(clean_param($p['alttext'], PARAM_TEXT), 0, self::MAX_ALT));
        if ($alt === '') {
            $alt = 'Agenda semanal';
        }
        $nombre = 'agenda_' . date('Ymd_His') . '.' . $ext;   // nombre propio: nunca el del cliente

        // 4) Elegir la etiqueta destino, en una transacción:
        //    - con targetcmid: una "Área de texto y medios" existente de General que TechCare adopta como la agenda;
        //    - sin targetcmid: la etiqueta propia del plugin (idnumber techcare_agenda), que se crea la primera vez.
        $tx = $DB->start_delegated_transaction();
        $labelmod = $DB->get_field('modules', 'id', ['name' => 'label'], MUST_EXIST);
        $creado = false;
        if (!empty($p['targetcmid'])) {
            $cm = $DB->get_record('course_modules', ['id' => $p['targetcmid'], 'course' => $course->id,
                                                     'module' => $labelmod, 'deletioninprogress' => 0]);
            if (!$cm) {
                throw new \moodle_exception('errortarget', 'local_techcareagenda');
            }
            $sec = $DB->get_record('course_sections', ['id' => $cm->section], 'section', MUST_EXIST);
            if ((int)$sec->section !== 0) {
                throw new \moodle_exception('errortarget', 'local_techcareagenda');   // solo la sección General
            }
            // Mantener UNA sola agenda gestionada: quitar la marca a cualquier otra y marcar la elegida.
            if ((string)$cm->idnumber !== self::IDNUMBER) {
                $DB->set_field_select('course_modules', 'idnumber', '',
                    'course = ? AND idnumber = ? AND id <> ?', [$course->id, self::IDNUMBER, $cm->id]);
                $DB->set_field('course_modules', 'idnumber', self::IDNUMBER, ['id' => $cm->id]);
                $cm->idnumber = self::IDNUMBER;
            }
        } else {
            $cm = $DB->get_record('course_modules', ['course' => $course->id, 'module' => $labelmod,
                                                     'idnumber' => self::IDNUMBER, 'deletioninprogress' => 0]);
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
        }

        $ctxmod = \context_module::instance($cm->id);
        $fs = get_file_storage();
        $fs->delete_area_files($ctxmod->id, 'mod_label', 'intro');   // REEMPLAZA: fuera la agenda anterior
        $fs->create_file_from_string(['contextid' => $ctxmod->id, 'component' => 'mod_label', 'filearea' => 'intro',
                                      'itemid' => 0, 'filepath' => '/', 'filename' => $nombre], $limpio);

        $html = '<p><img src="@@PLUGINFILE@@/' . rawurlencode($nombre) . '" alt="' . s($alt) .
                '" class="img-fluid" style="max-width:100%;height:auto"></p>';
        $DB->update_record('label', (object)['id' => $cm->instance, 'intro' => $html, 'introformat' => FORMAT_HTML,
                                             'name' => 'Agenda semanal', 'timemodified' => time()]);
        $tx->allow_commit();
        rebuild_course_cache($course->id, true);

        // 5) Queda en los registros de Moodle (Informes → Registros).
        \local_techcareagenda\event\agenda_publicada::create([
            'context' => $ctxcurso, 'objectid' => $cm->id,
            'other' => ['creado' => $creado, 'archivo' => $nombre, 'bytes' => strlen($limpio)],
        ])->trigger();

        return ['cmid' => (int)$cm->id, 'creado' => $creado,
                'url' => (new \moodle_url('/course/view.php', ['id' => $course->id]))->out(false)];
    }

    /** Si el administrador limitó las categorías, el curso debe estar en una de ellas (o en una subcategoría). */
    private static function validar_categoria(\stdClass $course): void {
        $lista = trim((string)get_config('local_techcareagenda', 'allowedcategories'));
        if ($lista === '') {
            return;
        }
        $permitidas = array_filter(array_map('intval', preg_split('/[\s,;]+/', $lista)));
        $cat = \core_course_category::get($course->category, IGNORE_MISSING, true);
        $ruta = $cat ? array_map('intval', explode('/', trim($cat->path, '/'))) : [];
        if (!array_intersect($permitidas, $ruta)) {
            throw new \moodle_exception('errorcategory', 'local_techcareagenda');
        }
    }

    /**
     * Valida la imagen por su contenido y la vuelve a generar con GD.
     * @return array [bytes limpios, extensión png|jpg]
     */
    private static function recodificar(string $bin): array {
        if (strlen($bin) > self::MAX_BYTES) {
            throw new \moodle_exception('errortoobig', 'local_techcareagenda', '', self::MAX_BYTES / 1048576);
        }
        $info = @getimagesizefromstring($bin);
        if (!$info || !in_array($info[2], [IMAGETYPE_PNG, IMAGETYPE_JPEG], true)) {
            throw new \moodle_exception('errorbadimage', 'local_techcareagenda');
        }
        [$ancho, $alto] = $info;
        if ($ancho < 1 || $alto < 1 || $ancho > self::MAX_LADO || $alto > self::MAX_LADO || $ancho * $alto > self::MAX_PIXELES) {
            throw new \moodle_exception('errordimensions', 'local_techcareagenda');
        }
        if (!function_exists('imagecreatefromstring')) {
            throw new \moodle_exception('errornogd', 'local_techcareagenda');
        }
        raise_memory_limit(MEMORY_EXTRA);
        $img = @imagecreatefromstring($bin);
        if (!$img) {
            throw new \moodle_exception('errorbadimage', 'local_techcareagenda');
        }
        ob_start();
        if ($info[2] === IMAGETYPE_PNG) {
            imagealphablending($img, false);
            imagesavealpha($img, true);
            $ok = imagepng($img, null, 6);
            $ext = 'png';
        } else {
            $ok = imagejpeg($img, null, 90);
            $ext = 'jpg';
        }
        $limpio = ob_get_clean();
        imagedestroy($img);
        if (!$ok || !$limpio) {
            throw new \moodle_exception('errorbadimage', 'local_techcareagenda');
        }
        return [$limpio, $ext];
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid'   => new external_value(PARAM_INT, 'ID del módulo de la agenda'),
            'creado' => new external_value(PARAM_BOOL, 'true si se creó por primera vez; false si se reemplazó'),
            'url'    => new external_value(PARAM_URL, 'Enlace al curso'),
        ]);
    }
}
