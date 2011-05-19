using System;
using System.Collections.Generic;
using System.Text;
using System.Windows;
using System.Collections;
using System.IO;
using System.Windows.Input;
using System.Windows.Controls;
using System.Collections.Specialized;
using CSP;

namespace DesktopApp
{

    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        // Commands
        public static readonly ICommand SignInCommand = new RoutedCommand("Sign in",typeof(MainWindow));
        public static readonly ICommand MountCommand = new RoutedCommand("Mount", typeof(MainWindow)); 

        // CSProxy Client
        CSPClient client = new CSPClient();
        // CSProxy FS
        CSPDokan dokan;
    
        public MainWindow()
        {
            InitializeComponent();
            Loaded += new RoutedEventHandler(MainWindow_Loaded);            
        }

        void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            // bind commands
            CommandBindings.Add(new CommandBinding(SignInCommand, OnSignInCommand, CanExecuteAuth));
            CommandBindings.Add(new CommandBinding(MountCommand, OnMountCommand, CanExecuteMount));

            // init drive letter comboBox
            foreach (char drive in getFreeDriveLetters())
            {
                cmbDrvLetter.Items.Add(drive); // add unused drive letters to the combo box
            }

            // init default service uri
            serviceUrl.Text = "https://vsd-storage.appspot.com/";

            // init dokan
            dokan = new CSPDokan(client);

            // event listeners
            // web browser listener
            wbAuth.Navigating += new System.Windows.Navigation.NavigatingCancelEventHandler(wbAuth_Navigating);
            // mount status listener
            dokan.IsMountedChanged += new CSPDokan.IsMountedChangeEventHandler(dokan_IsMountedChanged);
        }

        void dokan_IsMountedChanged(object sender, IsMountedChangeEventArgs e)
        {
            if (e.isMounted)
            {
                btnMount.Content = "Unmount";
                tbFsStatus.Text = "Mounted";
                tbDriveLetter.Text = e.driveLetter;
            }
            else
            {
                btnMount.Content = "Mount";
                if (e.status != 0)
                {
                    tbFsStatus.Text = "Error " + e.status;
                }
                else
                {
                    tbFsStatus.Text = "Unmounted";
                }
            }
        }

        /**
         * Navigation event handler
         * Used to catch dummy:// scheme
         */
        void wbAuth_Navigating(object sender, System.Windows.Navigation.NavigatingCancelEventArgs e)
        {
            if (e.Uri != null && e.Uri.Scheme == "dummy")
            {                
                e.Cancel = true;
                NameValueCollection query = ParseQueryString(e.Uri.Query);
                if (query["error"] != null)
                {
                    wbAuth.NavigateToString("<h1>" + query["error"] + "</h1>");
                }
                else if (query["authorization_code"] != null)
                {
                    if (client.authorize(query["authorization_code"]))
                    {
                        btnAuth.Content = "Sign out";
                        tbSrvStatus.Text = "Authorized";
                        wbAuth.NavigateToString("<h1>Successfully authorized</h1>");
                        authExpander.IsExpanded = false;
                        // enable Mount button
                        CommandManager.InvalidateRequerySuggested();
                    }
                    else
                    {
                        wbAuth.NavigateToString("<h1>Failed to retrieve access token</h1>");
                    }
                }
                else
                {
                    wbAuth.NavigateToString("<h1>The server returned an invalid or unrecognized response</h1>");
                }
            }            
        }        

        // Quick and straight-forward query string parsing
        private NameValueCollection ParseQueryString(string s)
        {
            NameValueCollection queryParameters = new NameValueCollection();
            string[] querySegments = s.Split('&');
            foreach (string segment in querySegments)
            {
                string[] parts = segment.Split('=');
                if (parts.Length > 0)
                {
                    string key = parts[0].Trim(new char[] { '?', ' ' });
                    string val = parts[1].Trim();

                    queryParameters.Add(key, val);
                }
            }
            return queryParameters;
        }

        private ArrayList getFreeDriveLetters()
        {
            ArrayList driveLetters = new ArrayList(26); // Allocate space for alphabet
            for (int i = 65; i < 91; i++) // increment from ASCII values for A-Z
            {
                driveLetters.Add(Convert.ToChar(i)); // Add uppercase letters to possible drive letters
            }

            foreach (string drive in Directory.GetLogicalDrives())
            {
                driveLetters.Remove(drive[0]); // removed used drive letters from possible drive letters
            }

            return driveLetters;
        }

        #region CommandHandlers
        void OnMountCommand(object sender, ExecutedRoutedEventArgs e)
        {
            // mount/umount
            if (dokan.isMounted)
            {
                dokan.Unmount();
            }
            else
            {
                dokan.Mount(cmbDrvLetter.SelectedValue.ToString());                
            }

        }

        void OnSignInCommand(object sender, ExecutedRoutedEventArgs e)
        {
            if (client.isAuthorized)
            {
                client.dropToken();
                // update status and buttons               
                btnAuth.Content = "Sign in";
                tbSrvStatus.Text = "Not Authorized";
                if (dokan.isMounted)
                {
                    dokan.Unmount();
                }
            }
            else
            {
                // TODO: add UI to toggle gdocs-link extension
                client.gdocsLinkExtension = true; // enable extension
                client.setBaseUri(serviceUrl.Text);
                wbAuth.Navigate(client.getAuthorizeUri("dummy://auth/"));
                authExpander.IsExpanded = true;
            }            
        }

        void CanExecuteMount(object sender, CanExecuteRoutedEventArgs e)
        {
            if (cmbDrvLetter.SelectedIndex >= 0 && client.isAuthorized)
                e.CanExecute = true;
        }

        void CanExecuteAuth(object sender, CanExecuteRoutedEventArgs e)
        {            
            e.CanExecute = true;           
        }

        #endregion                
    }

}
