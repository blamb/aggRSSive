<?php
/**
 * Plugin Name: aggRSSive Embed
 * Plugin URI:  https://github.com/blamb/aggRSSive
 * Description: A block and a shortcode that show a live aggRSSive (a filtered, curated feed bundle) on your site.
 * Version:     1.0.0
 * Author:      aggRSSive
 * License:     MIT
 * Text Domain: aggrssive-embed
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'AGGRSSIVE_EMBED_VERSION', '1.0.0' );

/** The aggRSSive site this WordPress talks to by default (Settings → aggRSSive). */
function aggrssive_embed_site() {
	$site = get_option( 'aggrssive_site', '' );
	return untrailingslashit( esc_url_raw( $site ) );
}

/** Normalise block/shortcode attributes to one array. */
function aggrssive_embed_args( $atts ) {
	$a = wp_parse_args(
		$atts,
		array(
			'site'   => '',
			'slug'   => '',
			'n'      => 10,
			'desc'   => 'excerpt', // excerpt | full | none
			'img'    => true,
			'src'    => true,
			'date'   => true,
			'theme'  => 'light',   // light | dark | auto
			'mode'   => 'script',  // script | iframe
			'height' => 500,
		)
	);
	$a['site']   = untrailingslashit( esc_url_raw( $a['site'] ? $a['site'] : aggrssive_embed_site() ) );
	$a['slug']   = preg_replace( '/[^a-z0-9]/', '', strtolower( (string) $a['slug'] ) );
	$a['n']      = max( 1, min( 100, intval( $a['n'] ) ) );
	$a['desc']   = in_array( $a['desc'], array( 'excerpt', 'full', 'none' ), true ) ? $a['desc'] : 'excerpt';
	$a['theme']  = in_array( $a['theme'], array( 'light', 'dark', 'auto' ), true ) ? $a['theme'] : 'light';
	$a['mode']   = 'iframe' === $a['mode'] ? 'iframe' : 'script';
	$a['height'] = max( 120, min( 2000, intval( $a['height'] ) ) );
	foreach ( array( 'img', 'src', 'date' ) as $k ) {
		$a[ $k ] = filter_var( $a[ $k ], FILTER_VALIDATE_BOOLEAN );
	}
	return $a;
}

/** HTML for one embed. Used by the block's server render and by the shortcode. */
function aggrssive_embed_html( $atts ) {
	$a = aggrssive_embed_args( $atts );
	if ( ! $a['site'] || ! $a['slug'] ) {
		return current_user_can( 'edit_posts' )
			? '<p><em>' . esc_html__( 'aggRSSive: choose an aggRSSive (its code) and make sure the site address is set under Settings → aggRSSive.', 'aggrssive-embed' ) . '</em></p>'
			: '';
	}
	if ( 'iframe' === $a['mode'] ) {
		$url = add_query_arg(
			array(
				'n'     => $a['n'],
				'desc'  => 'none' === $a['desc'] ? 0 : 1,
				'img'   => $a['img'] ? 1 : 0,
				'src'   => $a['src'] ? 1 : 0,
				'date'  => $a['date'] ? 1 : 0,
				'theme' => $a['theme'],
			),
			$a['site'] . '/embed/' . $a['slug'] . '/frame'
		);
		return sprintf(
			'<iframe class="aggrssive-frame" src="%s" width="100%%" height="%d" style="border:0" loading="lazy" title="%s"></iframe>',
			esc_url( $url ),
			$a['height'],
			esc_attr__( 'aggRSSive feed list', 'aggrssive-embed' )
		);
	}
	return sprintf(
		'<script src="%s" data-n="%d" data-desc="%s" data-img="%s" data-src="%s" data-date="%s" data-theme="%s"></script>',
		esc_url( $a['site'] . '/embed/' . $a['slug'] . '.js' ),
		$a['n'],
		esc_attr( 'none' === $a['desc'] ? '0' : ( 'full' === $a['desc'] ? 'full' : '1' ) ),
		$a['img'] ? '1' : '0',
		$a['src'] ? '1' : '0',
		$a['date'] ? '1' : '0',
		esc_attr( $a['theme'] )
	);
}

/** Shortcode: [aggrssive slug="abcd1234" n="8" desc="none" theme="dark" mode="iframe"] */
add_shortcode( 'aggrssive', 'aggrssive_embed_html' );

/** Block: aggrssive/embed, rendered on the server so the script tag is emitted exactly once, unmodified. */
function aggrssive_embed_register_block() {
	wp_register_script(
		'aggrssive-embed-editor',
		plugins_url( 'block.js', __FILE__ ),
		array( 'wp-blocks', 'wp-element', 'wp-components', 'wp-block-editor', 'wp-server-side-render', 'wp-i18n' ),
		AGGRSSIVE_EMBED_VERSION,
		true
	);
	wp_localize_script( 'aggrssive-embed-editor', 'aggrssiveEmbed', array( 'site' => aggrssive_embed_site() ) );
	register_block_type(
		'aggrssive/embed',
		array(
			'api_version'     => 2,
			'editor_script'   => 'aggrssive-embed-editor',
			'render_callback' => 'aggrssive_embed_html',
			'attributes'      => array(
				'site'   => array( 'type' => 'string', 'default' => '' ),
				'slug'   => array( 'type' => 'string', 'default' => '' ),
				'n'      => array( 'type' => 'number', 'default' => 10 ),
				'desc'   => array( 'type' => 'string', 'default' => 'excerpt' ),
				'img'    => array( 'type' => 'boolean', 'default' => true ),
				'src'    => array( 'type' => 'boolean', 'default' => true ),
				'date'   => array( 'type' => 'boolean', 'default' => true ),
				'theme'  => array( 'type' => 'string', 'default' => 'light' ),
				'mode'   => array( 'type' => 'string', 'default' => 'script' ),
				'height' => array( 'type' => 'number', 'default' => 500 ),
			),
		)
	);
}
add_action( 'init', 'aggrssive_embed_register_block' );

/** Settings → aggRSSive: the site address, so editors only need an aggRSSive's code. */
function aggrssive_embed_settings_init() {
	register_setting( 'aggrssive_embed', 'aggrssive_site', array( 'type' => 'string', 'sanitize_callback' => 'esc_url_raw', 'default' => '' ) );
	add_settings_section( 'aggrssive_embed_main', __( 'aggRSSive site', 'aggrssive-embed' ), '__return_false', 'aggrssive_embed' );
	add_settings_field(
		'aggrssive_site',
		__( 'Site address', 'aggrssive-embed' ),
		function () {
			printf( '<input type="url" name="aggrssive_site" value="%s" class="regular-text" placeholder="https://aggrssive.example.edu">', esc_attr( get_option( 'aggrssive_site', '' ) ) );
			echo '<p class="description">' . esc_html__( 'The aggRSSive install your lists live on. Each block or shortcode then only needs the aggRSSive\'s code (the part after /bundles/ in its address).', 'aggrssive-embed' ) . '</p>';
		},
		'aggrssive_embed',
		'aggrssive_embed_main'
	);
}
add_action( 'admin_init', 'aggrssive_embed_settings_init' );

function aggrssive_embed_settings_page() {
	add_options_page( 'aggRSSive', 'aggRSSive', 'manage_options', 'aggrssive_embed', 'aggrssive_embed_settings_render' );
}
add_action( 'admin_menu', 'aggrssive_embed_settings_page' );

function aggrssive_embed_settings_render() {
	echo '<div class="wrap"><h1>aggRSSive</h1><form method="post" action="options.php">';
	settings_fields( 'aggrssive_embed' );
	do_settings_sections( 'aggrssive_embed' );
	submit_button();
	echo '</form><p>' . esc_html__( 'Then add the "aggRSSive" block to any post or page, or use the shortcode:', 'aggrssive-embed' ) . ' <code>[aggrssive slug="abcd1234" n="8"]</code></p></div>';
}
