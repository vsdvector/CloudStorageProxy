<?php
include('utils.inc');

ini_set("session.cookie_domain", "z98128.infobox.ru");

session_start();

if ($_GET['login'] == 1) {
	// "authorize" user
	$_SESSION['logged'] = 1;
}

if ($_SESSION['logged'] == 0) {
	echo "Viewing as guest. <a href='/stor/?login=1'>login?</a>";
}

if ($_GET['authorization_code']) {
	// OAuth!!
	// get our token
	$url = 'https://vsd-storage.appspot.com/access_token';
	$fields = array('client_id' => 'webtest', 'pass' => 's3c|r3t', 'code' => $_GET['authorization_code']);
	$result = post($url, $fields);
	if($result[1] == 200) {		
		$token = json_decode($result[0]);
		$_SESSION['auth'] = $token->access_token; 
	} else {
		echo '<h2>Something went bad:</h2>';
		echo "Error code: $result[1] Content: $result[0]";
	}	
} 
// load config and data
@$data = unserialize(file_get_contents('data'));

if ($_GET['file'] && $_SESSION['auth']) {
	$url = 'https://vsd-storage.appspot.com/share'.$_GET['file'].'?oauth_token='.$_SESSION['auth'];				
	$result = post($url,array());	
	$data['image'] = 'http://vsd-storage.appspot.com/link/'.$result[0];
	file_put_contents('data',serialize($data));
	header('Location: http://z98128.infobox.ru/stor/');
	exit;
}

if ($_POST && $_SESSION['logged']) {
	if ($_POST['save']) {		
		$url = 'https://vsd-storage.appspot.com/files/test.txt?oauth_token='.$_SESSION['auth'];		
		$fields = array('file' => $data['content']);
		$result = post($url, $fields);
		if($result[1] == 200) {
			echo 'saved!';
		} else {		
			echo '<h2>Something went bad:</h2>';
			echo "Error code: $result[1] Content: $result[0]";
		}
	} else  {
		$data['content'] = $_POST['somecontent'];
		file_put_contents('data',serialize($data));
	}
}

echo "<div><h1>Some image:</h1><img src='".$data['image']."' /></div>";
echo "<div><h1>Some content:</h1>".$data['content'];
if($_SESSION['auth']) {
	echo "<form method='POST'><input type='submit' name='save' value='save'></input></form>";
}
echo "</div>";

if ($_SESSION['logged']) {
	echo	   '<div>
					<form method="POST">
						<textarea name="somecontent"></textarea>
						<input type="submit" />
					</form>
				</div>';
	echo '<div><h2>Your storage proxy token:';  
	$auth_url = "https://vsd-storage.appspot.com/authorize?client_id=webtest&redirect_uri=http://z98128.infobox.ru/stor/";
	$auth_link = "<a href='$auth_url'>No auth</a>";
	echo !$_SESSION['auth'] ? $auth_link : $_SESSION['auth'];  
	echo '</h2></div>'; 		
}

if($_SESSION['auth']) {
	echo '<div><h3>Your file list</h3>';
	$url = 'https://vsd-storage.appspot.com/metadata/?oauth_token='.$_SESSION['auth'];				
	$result = get($url);
	$metadata = json_decode($result[0]);
	echo '<ul>';
	foreach($metadata->content as $entry) {
		if(!$entry->is_dir) {
			echo '<li>'.$entry->path.' <a href="/stor?file='.$entry->path.'">use as image</a></li>';
		}
	}
	echo '</ul>';
	echo '</div>';
}
?> 
