using UnityEngine;
using UnityEngine.UI;

public class ReloadEffectController : MonoBehaviour
{
    public Button reloadButton;           
    public GameObject reloadPanel;
    public GunController gunController;
    private Animator reloadPanelAnimator; // Animator attached to the reload panel

    private void Start()
    {
        // Get the animator component
        reloadPanelAnimator = reloadPanel.GetComponent<Animator>();

        // Initially, the panel should be hidden
        // reloadPanel.SetActive(false);

        // Subscribe the function to the button click
        reloadButton.onClick.AddListener(ShowReloadEffect);
    }

    private void ShowReloadEffect()
    {
        // Check if the bullet count in GunController is 0
        
        if (gunController.bulletCount == 0)
        {
            gunController.Reload();
            // Activate the panel and play the animation
            reloadPanel.SetActive(true);
            reloadPanelAnimator.Play("ReloadPopup");

            // Deactivate the panel after the animation duration (1 seconds in this case)
            Invoke("HideReloadEffect", 1f);
        }
    }

    private void HideReloadEffect()
    {
        reloadPanel.SetActive(false);
    }

    public void PlayReloadEffect()
    {
        reloadPanel.SetActive(true);
        reloadPanelAnimator.Play("ReloadPopup");

        Invoke("HideReloadEffect", 1f);
    }
}

