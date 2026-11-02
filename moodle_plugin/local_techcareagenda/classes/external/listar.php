<?php
// Lista las imágenes que YA hay en la sección General (sección 0) del curso, para que TechCare deje
// elegir cuál reemplazar con la agenda. Es de SOLO LECTURA: no cambia nada en el curso.
//
// Por cada actividad de la sección General con una imagen devuelve: cmid, nombre, tipo (modname),
// nombre de archivo, una MINIATURA (JPEG pequeño en base64 para previsualizar), si es reemplazable
// (solo las "Área de texto y medios" = label se pueden reemplazar de forma segura) y si ya es la
// agenda que gestiona TechCare (idnumber techcare_agenda).
namespace local_techcareagenda\external;

defined('MOODLE_INTERNAL') || die();

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_multiple_structure;
use core_external\external_single_structure;
use core_external\external_value;

class listar extends external_api {

    const MINIATURA_LADO = 200;   // px del lado mayor de la miniatura de previsualización

    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'ID del curso'),
        ]);
    }

    public static function execute(int $courseid): array {
        global $DB;
        $p = self::validate_parameters(self::execute_parameters(), compact('courseid'));

        if ($p['courseid'] == SITEID) {
            throw new \moodle_exception('errorcourse', 'local_techcareagenda');
        }
        $course = get_course($p['courseid']);
        $ctxcurso = \context_course::instance($course->id);
        self::validate_context($ctxcurso);
        // Para listar lo que PODRÍA reemplazar exigimos el mismo permiso de gestión del curso.
        require_capability('moodle/course:manageactivities', $ctxcurso);

        // Áreas de archivos donde suele vivir la imagen de cada tipo de actividad.
        $areas = [
            'label'    => ['mod_label', 'intro'],
            'resource' => ['mod_resource', 'content'],
        ];

        $fs = get_file_storage();
        $modinfo = get_fast_modinfo($course);
        $items = [];
        foreach ($modinfo->get_cms() as $cm) {
            if ($cm->sectionnum != 0 || $cm->deletioninprogress) {
                continue;   // solo la sección General
            }
            if (!isset($areas[$cm->modname])) {
                continue;   // solo tipos con imagen conocida (label / resource)
            }
            [$component, $filearea] = $areas[$cm->modname];
            $ctxmod = \context_module::instance($cm->id);
            $archivos = $fs->get_area_files($ctxmod->id, $component, $filearea, false, 'filename', false);
            $imagen = null;
            foreach ($archivos as $f) {
                if ($f->is_valid_image()) {
                    $imagen = $f;
                    break;
                }
            }
            if (!$imagen) {
                continue;   // la actividad no tiene imagen: no interesa para reemplazar
            }
            $items[] = [
                'cmid'        => (int)$cm->id,
                'nombre'      => \core_text::substr(format_string($cm->name), 0, 120),
                'modname'     => $cm->modname,
                'archivo'     => $imagen->get_filename(),
                'miniatura'   => self::miniatura($imagen),
                'reemplazable' => $cm->modname === 'label',
                'esagenda'    => ((string)$cm->idnumber === publicar::IDNUMBER),
            ];
        }

        return ['items' => $items];
    }

    /** Miniatura JPEG pequeña (data URI) para previsualizar; '' si no se pudo generar. */
    private static function miniatura(\stored_file $file): string {
        if (!function_exists('imagecreatefromstring') || $file->get_filesize() > publicar::MAX_BYTES) {
            return '';
        }
        $bin = $file->get_content();
        $info = @getimagesizefromstring($bin);
        if (!$info) {
            return '';
        }
        raise_memory_limit(MEMORY_EXTRA);
        $src = @imagecreatefromstring($bin);
        unset($bin);
        if (!$src) {
            return '';
        }
        $w = imagesx($src);
        $h = imagesy($src);
        $escala = min(1, self::MINIATURA_LADO / max($w, $h));
        $nw = max(1, (int)round($w * $escala));
        $nh = max(1, (int)round($h * $escala));
        $dst = imagecreatetruecolor($nw, $nh);
        imagecopyresampled($dst, $src, 0, 0, 0, 0, $nw, $nh, $w, $h);
        ob_start();
        $ok = imagejpeg($dst, null, 75);
        $out = ob_get_clean();
        imagedestroy($src);
        imagedestroy($dst);
        return ($ok && $out) ? 'data:image/jpeg;base64,' . base64_encode($out) : '';
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'items' => new external_multiple_structure(new external_single_structure([
                'cmid'         => new external_value(PARAM_INT, 'ID del módulo'),
                'nombre'       => new external_value(PARAM_TEXT, 'Nombre de la actividad'),
                'modname'      => new external_value(PARAM_ALPHANUMEXT, 'Tipo de actividad (label, resource)'),
                'archivo'      => new external_value(PARAM_FILE, 'Nombre del archivo de imagen'),
                'miniatura'    => new external_value(PARAM_RAW, 'Miniatura JPEG en data URI (puede ir vacía)'),
                'reemplazable' => new external_value(PARAM_BOOL, 'true si TechCare puede reemplazar su imagen'),
                'esagenda'     => new external_value(PARAM_BOOL, 'true si ya es la agenda que gestiona TechCare'),
            ])),
        ]);
    }
}
